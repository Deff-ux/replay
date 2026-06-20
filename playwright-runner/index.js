const express = require('express');
const fs = require('fs/promises');
const path = require('path');
const { chromium } = require('playwright');
const { Pool } = require('pg');
const { v4: uuidv4 } = require('uuid');
const winston = require('winston');

const PORT = Number.parseInt(process.env.PORT || '8550', 10);
const HOST = process.env.HOST || '0.0.0.0';
const ARTIFACT_DIR = process.env.ARTIFACT_DIR || '/artifacts';
const MAX_PARALLEL_WORKERS = Number.parseInt(process.env.MAX_PARALLEL_WORKERS || '3', 10);
const REQUESTS_PER_IP_PER_SECOND = 1;
const allowedIpPrefixes = (process.env.IP_ALLOWLIST || '127.0.0.1,::1,::ffff:127.0.0.1,172.,10.,192.168.')
  .split(',')
  .map((prefix) => prefix.trim())
  .filter(Boolean);

const app = express();
app.set('trust proxy', true);
app.use(express.json({ limit: '1mb' }));

const pool = new Pool({
  connectionString: process.env.DB_CONNECTION,
  max: 5,
  idleTimeoutMillis: 30000,
});

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(winston.format.timestamp(), winston.format.errors({ stack: true }), winston.format.json()),
  defaultMeta: { service: 'playwright-runner' },
  transports: [new winston.transports.Console()],
});

if (process.env.LOG_TO_FILES !== 'false') {
  logger.add(new winston.transports.File({ filename: '/var/log/testdashboard/error.log', level: 'error' }));
  logger.add(new winston.transports.File({ filename: '/var/log/testdashboard/combined.log' }));
}

const rateLimit = new Map();
const runningBrowsers = new Set();
let acceptingRequests = true;
let server;
let lastNotificationTime = 0;

function asyncRoute(handler) {
  return (req, res, next) => Promise.resolve(handler(req, res, next)).catch(next);
}

app.use((req, res, next) => {
  if (!acceptingRequests) return res.status(503).json({ error: 'Service shutting down' });
  const ip = req.ip || req.socket.remoteAddress || '';
  if (!allowedIpPrefixes.some((prefix) => ip.startsWith(prefix))) {
    logger.warn('Blocked request from non-allowlisted IP', { ip, path: req.path });
    return res.status(403).json({ error: 'Forbidden' });
  }
  const now = Date.now();
  const windowStart = now - 1000;
  const requests = (rateLimit.get(ip) || []).filter((timestamp) => timestamp > windowStart);
  if (requests.length >= REQUESTS_PER_IP_PER_SECOND) return res.status(429).json({ error: 'Too many requests' });
  requests.push(now);
  rateLimit.set(ip, requests);
  return next();
});

app.get('/api/health', asyncRoute(async (_req, res) => {
  const db = await pool.query('SELECT 1').then(() => true).catch(() => false);
  const artifacts = await fs.access(ARTIFACT_DIR).then(() => true).catch(() => false);
  res.status(db && artifacts ? 200 : 503).json({
    status: db && artifacts ? 'healthy' : 'degraded',
    db,
    artifacts,
    uptime: process.uptime(),
  });
}));

app.post('/api/run', asyncRoute(async (req, res) => {
  const { testCaseId, environment = 'staging' } = req.body;
  if (!testCaseId) return res.status(400).json({ error: 'testCaseId required' });
  if (!isValidEnvironment(environment)) return res.status(400).json({ error: 'Invalid environment' });

  const runId = uuidv4();
  await createRun({ runId, testCaseId, environment, total: 1 });
  setImmediate(() => executeSingleRun(runId, testCaseId, environment).catch((error) => logger.error('Run failed', { runId, error: error.message })));
  return res.status(202).json({ runId, status: 'queued' });
}));

app.post('/api/suite', asyncRoute(async (req, res) => {
  const { suiteId, environment = 'staging' } = req.body;
  if (!suiteId) return res.status(400).json({ error: 'suiteId required' });
  if (!isValidEnvironment(environment)) return res.status(400).json({ error: 'Invalid environment' });

  const suite = await pool.query('SELECT test_case_ids FROM suites WHERE id = $1', [suiteId]);
  if (!suite.rows.length) return res.status(404).json({ error: 'Suite not found' });

  const testIds = suite.rows[0].test_case_ids || [];
  const runId = uuidv4();
  await createRun({ runId, suiteId, environment, total: testIds.length });
  setImmediate(() => executeSuiteParallel(runId, testIds, environment).catch((error) => logger.error('Suite failed', { runId, error: error.message })));
  return res.status(202).json({ runId, status: 'queued', totalTests: testIds.length, parallel: getMaxParallel(testIds.length) });
}));

app.get('/api/status/:runId', asyncRoute(async (req, res) => {
  const result = await pool.query('SELECT run_id, status, progress, total, passed, failed, result, started_at, finished_at FROM test_runs WHERE run_id = $1', [req.params.runId]);
  if (!result.rows.length) return res.status(404).json({ error: 'Run not found' });
  return res.json(result.rows[0]);
}));

app.get('/api/artifacts/:runId/*', asyncRoute(async (req, res) => {
  const relativePath = req.params[0];
  if (!relativePath || relativePath.includes('..')) return res.status(400).json({ error: 'Invalid artifact path' });

  const artifact = await pool.query(
    'SELECT file_path, artifact_type FROM artifact_files WHERE run_id = $1 AND public_path = $2',
    [req.params.runId, `/api/artifacts/${req.params.runId}/${relativePath}`],
  );
  if (!artifact.rows.length) return res.status(404).json({ error: 'Artifact not found' });

  const absolutePath = path.resolve(artifact.rows[0].file_path);
  const artifactRoot = path.resolve(ARTIFACT_DIR);
  if (!absolutePath.startsWith(artifactRoot)) return res.status(403).json({ error: 'Forbidden' });

  return res.sendFile(absolutePath);
}));

app.use((error, req, res, _next) => {
  logger.error('Unhandled API error', { path: req.path, error: error.message, stack: error.stack });
  res.status(500).json({ error: 'Internal server error' });
});

async function createRun({ runId, suiteId = null, testCaseId = null, environment, total }) {
  await pool.query(
    `INSERT INTO test_runs (run_id, suite_id, test_case_id, status, total, environment, triggered_by, created_at)
     VALUES ($1, $2, $3, 'queued', $4, $5, 'manual', NOW())`,
    [runId, suiteId, testCaseId, total, environment],
  );
  await logActivity('run_queued', suiteId ? 'suite' : 'test_case', suiteId || testCaseId, { runId, environment, total });
}

async function executeSingleRun(runId, testCaseId, environment) {
  await pool.query("UPDATE test_runs SET status = 'running', started_at = NOW() WHERE run_id = $1", [runId]);
  const result = await executeSingleTestWithRetry(testCaseId, environment, runId);
  await finishRun(runId, [result]);
}

async function executeSuiteParallel(runId, testIds, environment) {
  await pool.query("UPDATE test_runs SET status = 'running', started_at = NOW() WHERE run_id = $1", [runId]);
  if (testIds.length === 0) return finishRun(runId, []);

  const results = [];
  let cursor = 0;
  async function worker() {
    while (cursor < testIds.length) {
      const testId = testIds[cursor];
      cursor += 1;
      const result = await executeSingleTestWithRetry(testId, environment, runId);
      results.push(result);
      await updateProgress(runId, results.length, testIds.length);
    }
  }

  await Promise.allSettled(Array.from({ length: getMaxParallel(testIds.length) }, worker));
  return finishRun(runId, results);
}

async function executeSingleTestWithRetry(testId, environment, runId) {
  const first = await executeSingleTest(testId, environment, runId);
  if (!first.passed && String(first.error || '').toLowerCase().includes('timeout')) {
    logger.warn('Retrying timeout failure once', { runId, testId });
    const second = await executeSingleTest(testId, environment, runId, 1);
    return { ...second, retried: true, firstError: first.error };
  }
  return first;
}

async function executeSingleTest(testId, environment, runId, attempt = 0) {
  const startTime = Date.now();
  let browser;
  try {
    const testCase = await pool.query('SELECT steps, assertions FROM test_cases WHERE id = $1 AND status = $2', [testId, 'active']);
    if (!testCase.rows.length) throw new Error('Active test case not found');

    browser = await chromium.launch({ headless: true });
    runningBrowsers.add(browser);
    const runDir = path.join(ARTIFACT_DIR, runId, String(testId), `attempt-${attempt}`);
    await fs.mkdir(runDir, { recursive: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: runDir } });
    const page = await context.newPage();
    let videoPath = null;

    const steps = testCase.rows[0].steps || [];
    for (let i = 0; i < steps.length; i += 1) {
      try {
        await executeStep(page, steps[i], environment);
        const screenshotPath = path.join(runDir, `step-${i}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true });
        await redactSensitiveAreas(screenshotPath);
        await registerArtifact(runId, testId, 'screenshot', screenshotPath);
        await logActivity('step_finish', 'test_case', testId, { runId, step: i, attempt });
      } catch (error) {
        const screenshotPath = path.join(runDir, `step-${i}-error.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => null);
        await redactSensitiveAreas(screenshotPath);
        await registerArtifact(runId, testId, 'screenshot', screenshotPath);
        logger.error('Step failed', { runId, testId, step: i, attempt, error: error.message });
        videoPath = await page.video()?.path().catch(() => null);
        await context.close().catch(() => null);
        if (videoPath) await registerArtifact(runId, testId, 'video', videoPath);
        return { testId, passed: false, step: i, error: error.message, duration: Date.now() - startTime };
      }
    }

    const assertions = testCase.rows[0].assertions || [];
    for (let i = 0; i < assertions.length; i += 1) await executeAssertion(page, assertions[i]);
    videoPath = await page.video()?.path().catch(() => null);
    await context.close();
    if (videoPath) await registerArtifact(runId, testId, 'video', videoPath);
    return { testId, passed: true, duration: Date.now() - startTime };
  } catch (error) {
    logger.error('Test execution failed', { runId, testId, attempt, error: error.message });
    return { testId, passed: false, error: error.message, duration: Date.now() - startTime };
  } finally {
    if (browser) {
      runningBrowsers.delete(browser);
      await browser.close().catch(() => null);
    }
  }
}

async function executeStep(page, step, environment) {
  const action = step.action;
  if (action === 'goto') return page.goto(await resolveUrl(step.url, environment), { waitUntil: step.waitUntil || 'networkidle', timeout: step.timeout || 30000 });
  if (action === 'click') return page.click(step.selector, { timeout: step.timeout || 30000 });
  if (action === 'fill') return page.fill(step.selector, step.value || '', { timeout: step.timeout || 30000 });
  if (action === 'waitForSelector') return page.waitForSelector(step.selector, { timeout: step.timeout || 30000 });
  if (action === 'expectVisible') return page.locator(step.selector).waitFor({ state: 'visible', timeout: step.timeout || 30000 });
  throw new Error(`Unsupported step action: ${action}`);
}

async function executeAssertion(page, assertion) {
  if (assertion.type === 'visible') return page.locator(assertion.selector).waitFor({ state: 'visible', timeout: assertion.timeout || 30000 });
  if (assertion.type === 'urlContains') {
    if (!page.url().includes(assertion.value)) throw new Error(`URL does not contain ${assertion.value}`);
    return null;
  }
  if (assertion.type === 'textContains') {
    const text = await page.locator(assertion.selector).innerText({ timeout: assertion.timeout || 30000 });
    if (!text.includes(assertion.value)) throw new Error(`Text does not contain ${assertion.value}`);
    return null;
  }
  throw new Error(`Unsupported assertion type: ${assertion.type}`);
}

async function resolveUrl(url, environment) {
  if (!url) throw new Error('goto step requires url');
  if (/^https?:\/\//i.test(url)) return url;
  const result = await pool.query('SELECT base_url FROM environments WHERE name = $1 AND is_active = true', [environment]);
  if (!result.rows.length) throw new Error(`Active environment not found: ${environment}`);
  return new URL(url, result.rows[0].base_url).toString();
}

async function finishRun(runId, results) {
  const passed = results.filter((result) => result.passed).length;
  const failed = results.length - passed;
  const status = failed > 0 ? 'failed' : 'completed';
  await pool.query(
    `UPDATE test_runs SET status = $1, progress = 100, passed = $2, failed = $3,
     result = $4, duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::INT, finished_at = NOW()
     WHERE run_id = $5`,
    [status, passed, failed, JSON.stringify(results), runId],
  );
  await logActivity('run_finished', 'test_run', runId, { status, passed, failed });
  if (failed > 0) await sendTelegramNotification(runId, passed, failed, results);
}

async function updateProgress(runId, completed, total) {
  await pool.query('UPDATE test_runs SET progress = $1 WHERE run_id = $2', [total ? Math.round((completed / total) * 100) : 100, runId]);
}

async function registerArtifact(runId, testCaseId, artifactType, filePath) {
  if (!filePath) return;
  const stat = await fs.stat(filePath).catch(() => null);
  if (!stat) return;
  const relativePath = path.relative(path.join(ARTIFACT_DIR, runId), filePath).split(path.sep).join('/');
  const publicPath = `/api/artifacts/${runId}/${relativePath}`;
  await pool.query(
    `INSERT INTO artifact_files (run_id, test_case_id, artifact_type, file_path, public_path, file_size_bytes)
     VALUES ($1, $2, $3, $4, $5, $6)`,
    [runId, testCaseId, artifactType, filePath, publicPath, stat.size],
  ).catch((error) => logger.warn('Failed to register artifact', { runId, testCaseId, artifactType, error: error.message }));
}

async function logActivity(action, targetType, targetId, metadata) {
  await pool.query('INSERT INTO activity_log(action, target_type, target_id, metadata) VALUES ($1, $2, $3, $4)', [action, targetType, targetId, metadata]).catch((error) => logger.warn('Failed to write activity log', { error: error.message }));
}

async function redactSensitiveAreas(_imagePath) {
  // MVP hook: all screenshots pass through this function before artifact retention.
}

async function sendTelegramNotification(runId, passed, failed, results) {
  const now = Date.now();
  if (now - lastNotificationTime < 60000) return;
  if (!process.env.TELEGRAM_BOT_TOKEN || !process.env.TELEGRAM_CHAT_ID) return;
  lastNotificationTime = now;
  const failures = results.filter((result) => !result.passed).slice(0, 5).map((result) => `• ${result.testId}: ${result.error || 'failed'}`).join('\n');
  const text = `❌ Test Failed — ${failed} of ${passed + failed} tests\n\n${failures}\n\nLink: ${process.env.PUBLIC_BASE_URL || 'https://test.defrinogionaldo.com'}/runs/${runId}`;
  try {
    await fetch(`https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: process.env.TELEGRAM_CHAT_ID, text }),
    });
  } catch (error) {
    logger.error('Failed to send Telegram notification', { runId, error: error.message });
  }
}

function isValidEnvironment(environment) {
  return ['staging', 'production', 'dev'].includes(environment);
}

function getMaxParallel(total) {
  return Math.max(1, Math.min(MAX_PARALLEL_WORKERS, 3, total || 1));
}

async function shutdown(signal) {
  logger.info('Shutdown signal received', { signal });
  acceptingRequests = false;
  if (server) server.close();
  await pool.query("UPDATE test_runs SET status = 'interrupted', finished_at = NOW() WHERE status = 'running'").catch((error) => logger.error('Failed to mark interrupted runs', { error: error.message }));
  await Promise.allSettled(Array.from(runningBrowsers).map((browser) => browser.close()));
  await pool.end().catch(() => null);
  process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

server = app.listen(PORT, HOST, () => logger.info('Playwright Runner listening', { host: HOST, port: PORT }));
