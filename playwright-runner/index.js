const express = require('express');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const { Pool } = require('pg');
const { v4: uuidv4 } = require('uuid');
const winston = require('winston');

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
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  defaultMeta: { service: 'playwright-runner' },
  transports: [
    new winston.transports.File({ filename: '/var/log/testdashboard/error.log', level: 'error' }),
    new winston.transports.File({ filename: '/var/log/testdashboard/combined.log' }),
    new winston.transports.Console(),
  ],
});

const allowedIpPrefixes = ['127.0.0.1', '::1', '::ffff:127.0.0.1', '172.', '10.', '192.168.'];
const rateLimit = new Map();
const runningBrowsers = new Set();
let acceptingRequests = true;
let server;
let lastNotificationTime = 0;

app.use((req, res, next) => {
  if (!acceptingRequests) return res.status(503).json({ error: 'Service shutting down' });
  const ip = req.ip || req.socket.remoteAddress || '';
  if (!allowedIpPrefixes.some((prefix) => ip.startsWith(prefix))) {
    logger.warn('Blocked request', { ip, path: req.path });
    return res.status(403).json({ error: 'Forbidden' });
  }
  const now = Date.now();
  const previous = rateLimit.get(ip) || 0;
  if (now - previous < 1000) return res.status(429).json({ error: 'Too many requests' });
  rateLimit.set(ip, now);
  next();
});

app.get('/api/health', async (_req, res) => {
  const db = await pool.query('SELECT 1').then(() => true).catch(() => false);
  const artifactOk = fs.existsSync('/artifacts');
  res.status(db && artifactOk ? 200 : 503).json({
    status: db && artifactOk ? 'healthy' : 'degraded',
    db,
    artifacts: artifactOk,
    uptime: process.uptime(),
  });
});

app.post('/api/run', async (req, res) => {
  const { testCaseId, environment = 'staging' } = req.body;
  if (!testCaseId) return res.status(400).json({ error: 'testCaseId required' });
  if (!isValidEnvironment(environment)) return res.status(400).json({ error: 'Invalid environment' });

  const runId = uuidv4();
  await createRun({ runId, testCaseId, environment, total: 1 });
  executeSingleRun(runId, testCaseId, environment).catch((error) => logger.error('Run failed', { runId, error: error.message }));
  res.json({ runId, status: 'queued' });
});

app.post('/api/suite', async (req, res) => {
  const { suiteId, environment = 'staging' } = req.body;
  if (!suiteId) return res.status(400).json({ error: 'suiteId required' });
  if (!isValidEnvironment(environment)) return res.status(400).json({ error: 'Invalid environment' });

  const suite = await pool.query('SELECT test_case_ids FROM suites WHERE id = $1', [suiteId]);
  if (!suite.rows.length) return res.status(404).json({ error: 'Suite not found' });

  const testIds = suite.rows[0].test_case_ids || [];
  const runId = uuidv4();
  await createRun({ runId, suiteId, environment, total: testIds.length });
  executeSuiteParallel(runId, testIds, environment).catch((error) => logger.error('Suite failed', { runId, error: error.message }));
  res.json({ runId, status: 'queued', totalTests: testIds.length, parallel: getMaxParallel(testIds.length) });
});

app.get('/api/status/:runId', async (req, res) => {
  const result = await pool.query('SELECT status, progress, total, passed, failed, result FROM test_runs WHERE run_id = $1', [req.params.runId]);
  if (!result.rows.length) return res.status(404).json({ error: 'Run not found' });
  res.json(result.rows[0]);
});

async function createRun({ runId, suiteId = null, testCaseId = null, environment, total }) {
  await pool.query(
    `INSERT INTO test_runs (run_id, suite_id, test_case_id, status, total, environment, triggered_by, created_at)
     VALUES ($1, $2, $3, 'queued', $4, $5, 'manual', NOW())`,
    [runId, suiteId, testCaseId, total, environment],
  );
}

async function executeSingleRun(runId, testCaseId, environment) {
  await pool.query("UPDATE test_runs SET status = 'running', started_at = NOW() WHERE run_id = $1", [runId]);
  const result = await executeSingleTest(testCaseId, environment, runId);
  await finishRun(runId, [result]);
}

async function executeSuiteParallel(runId, testIds, environment) {
  await pool.query("UPDATE test_runs SET status = 'running', started_at = NOW() WHERE run_id = $1", [runId]);
  const results = [];
  let cursor = 0;
  const workerCount = getMaxParallel(testIds.length);

  async function worker() {
    while (cursor < testIds.length) {
      const testId = testIds[cursor++];
      const result = await executeSingleTest(testId, environment, runId);
      results.push(result);
      await updateProgress(runId, results.length, testIds.length);
    }
  }

  await Promise.allSettled(Array.from({ length: workerCount }, worker));
  await finishRun(runId, results);
}

async function executeSingleTest(testId, environment, runId) {
  const startTime = Date.now();
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    runningBrowsers.add(browser);
    const runDir = path.join('/artifacts', runId, String(testId));
    fs.mkdirSync(runDir, { recursive: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: runDir } });
    const page = await context.newPage();
    const testCase = await pool.query('SELECT steps FROM test_cases WHERE id = $1 AND status = $2', [testId, 'active']);
    if (!testCase.rows.length) throw new Error('Active test case not found');

    const steps = testCase.rows[0].steps || [];
    for (let i = 0; i < steps.length; i += 1) {
      try {
        await executeStep(page, steps[i], environment);
        const screenshotPath = path.join(runDir, `step-${i}.png`);
        await page.screenshot({ path: screenshotPath });
        await redactSensitiveAreas(screenshotPath);
        await logActivity('step_finish', 'test_case', testId, { runId, step: i });
      } catch (error) {
        const screenshotPath = path.join(runDir, `step-${i}-error.png`);
        await page.screenshot({ path: screenshotPath }).catch(() => null);
        await redactSensitiveAreas(screenshotPath);
        logger.error('Step failed', { runId, testId, step: i, error: error.message });
        return { testId, passed: false, step: i, error: error.message, duration: Date.now() - startTime };
      }
    }
    await context.close();
    return { testId, passed: true, duration: Date.now() - startTime };
  } catch (error) {
    logger.error('Test execution failed', { runId, testId, error: error.message });
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
  if (action === 'goto') return page.goto(resolveUrl(step.url, environment), { waitUntil: 'networkidle' });
  if (action === 'click') return page.click(step.selector);
  if (action === 'fill') return page.fill(step.selector, step.value || '');
  if (action === 'waitForSelector') return page.waitForSelector(step.selector, { timeout: step.timeout || 30000 });
  if (action === 'expectVisible') return page.locator(step.selector).waitFor({ state: 'visible', timeout: step.timeout || 30000 });
  throw new Error(`Unsupported step action: ${action}`);
}

function resolveUrl(url) {
  return url;
}

async function finishRun(runId, results) {
  const passed = results.filter((result) => result.passed).length;
  const failed = results.length - passed;
  await pool.query(
    `UPDATE test_runs SET status = 'completed', progress = 100, passed = $1, failed = $2,
     result = $3, duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::INT, finished_at = NOW()
     WHERE run_id = $4`,
    [passed, failed, JSON.stringify(results), runId],
  );
  if (failed > 0) await sendTelegramNotification(runId, passed, failed, results);
}

async function updateProgress(runId, completed, total) {
  const progress = total ? Math.round((completed / total) * 100) : 100;
  await pool.query('UPDATE test_runs SET progress = $1 WHERE run_id = $2', [progress, runId]);
}

async function logActivity(action, targetType, targetId, metadata) {
  await pool.query('INSERT INTO activity_log(action, target_type, target_id, metadata) VALUES ($1, $2, $3, $4)', [action, targetType, targetId, metadata]);
}

async function redactSensitiveAreas(_imagePath) {
  // MVP placeholder: keep hook centralized so sharp-based redaction can be added without changing execution flow.
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
  return Math.max(1, Math.min(Number.parseInt(process.env.MAX_PARALLEL_WORKERS || '3', 10), total || 1));
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

const PORT = process.env.PORT || 8550;
server = app.listen(PORT, '127.0.0.1', () => logger.info('Playwright Runner listening', { port: PORT }));
