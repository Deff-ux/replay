#!/usr/bin/env node
/*
 * Replay Budibase bootstrapper.
 *
 * The Budibase public API shape can vary between releases. This script keeps all
 * calls small and explicit, retries transient failures, and prints a structured
 * JSON setup report so operators can see which resources were created or
 * already existed.
 */

const BUDIBASE_URL = (process.env.BUDIBASE_URL || 'http://budibase:80').replace(/\/$/, '')
const BUDIBASE_USER = process.env.BUDIBASE_USER || process.env.BUDIBASE_EMAIL || 'admin@example.com'
const BUDIBASE_PASSWORD = process.env.BUDIBASE_PASSWORD || process.env.BB_ADMIN_PASSWORD || 'admin'
const DB_PASSWORD = process.env.DB_PASSWORD

if (!DB_PASSWORD) {
  throw new Error('DB_PASSWORD is required and must be provided via environment variable')
}

const APP_NAME = process.env.BUDIBASE_APP_NAME || 'Replay Test Dashboard'
const DB_CONFIG = {
  host: process.env.DB_HOST || 'postgres',
  port: Number(process.env.DB_PORT || 5432),
  database: process.env.DB_NAME || 'testdashboard',
  user: process.env.DB_USER || 'budibase',
  password: DB_PASSWORD,
}

const editableTables = ['test_cases', 'suites', 'environments']
const readOnlyTables = ['test_runs', 'artifact_files']
const readOnlyViews = [
  'budibase_dashboard_product_cards',
  'budibase_dashboard_summary',
  'budibase_test_case_list',
  'budibase_run_results',
  'budibase_run_detail',
]

const screens = [
  {
    name: 'Dashboard',
    route: '/',
    sources: ['budibase_dashboard_summary', 'budibase_dashboard_product_cards'],
    widgets: ['summary metrics', 'product status cards', 'pass rate', 'queued/running counters'],
  },
  {
    name: 'Test Cases',
    route: '/test-cases',
    sources: ['budibase_test_case_list'],
    widgets: ['searchable table', 'product/status/tags filters', 'open Test Detail action'],
  },
  {
    name: 'Test Detail',
    route: '/test-cases/:id',
    sources: ['test_cases', 'test_runs'],
    widgets: ['editable steps form', 'editable assertions form', 'related run history'],
  },
  {
    name: 'Run Results',
    route: '/runs',
    sources: ['budibase_run_results'],
    widgets: ['filterable run table', 'status/product filters', 'CSV export'],
  },
  {
    name: 'Run Detail',
    route: '/runs/:id',
    sources: ['budibase_run_detail'],
    widgets: ['metadata panel', 'JSON result viewer', 'artifact links'],
  },
  {
    name: 'Suites',
    route: '/suites',
    sources: ['suites', 'test_cases'],
    widgets: ['CRUD form', 'ordered test_case_ids assignment', 'schedule controls'],
  },
  {
    name: 'Environments',
    route: '/environments',
    sources: ['environments'],
    widgets: ['CRUD table', 'base URL form'],
  },
]

const report = { budibaseUrl: BUDIBASE_URL, appName: APP_NAME, created: [], skipped: [], failed: [] }

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

async function request(path, options = {}, attempt = 1) {
  const headers = {
    'content-type': 'application/json',
    ...(options.token ? { authorization: `Bearer ${options.token}`, 'x-budibase-api-key': options.token } : {}),
    ...(options.headers || {}),
  }
  const response = await fetch(`${BUDIBASE_URL}${path}`, { ...options, headers })
  const bodyText = await response.text()
  let body
  try {
    body = bodyText ? JSON.parse(bodyText) : {}
  } catch {
    body = { raw: bodyText }
  }

  if (!response.ok) {
    const transient = response.status === 408 || response.status === 429 || response.status >= 500
    if (transient && attempt < 3) {
      await sleep(500 * attempt)
      return request(path, options, attempt + 1)
    }
    const error = new Error(`${options.method || 'GET'} ${path} failed with ${response.status}`)
    error.status = response.status
    error.body = body
    throw error
  }
  return body
}

async function tryRequest(label, path, options, optional = false) {
  try {
    const result = await request(path, options)
    report.created.push({ label, path, id: result._id || result.id || result.data?._id || result.data?.id || null })
    return result
  } catch (error) {
    const entry = { label, path, status: error.status || null, message: error.message, body: error.body || null }
    if (optional || error.status === 409) {
      report.skipped.push(entry)
      return null
    }
    report.failed.push(entry)
    throw error
  }
}

async function login() {
  const candidates = [
    ['/api/public/v1/users/login', { email: BUDIBASE_USER, password: BUDIBASE_PASSWORD }],
    ['/api/global/auth/default/login', { username: BUDIBASE_USER, email: BUDIBASE_USER, password: BUDIBASE_PASSWORD }],
  ]

  for (const [path, body] of candidates) {
    try {
      const result = await request(path, { method: 'POST', body: JSON.stringify(body) })
      const token = result.token || result.jwt || result.data?.token || result.data?.jwt
      if (token) return token
      report.skipped.push({ label: 'login-token', path, message: 'Login succeeded but no token was returned' })
    } catch (error) {
      report.skipped.push({ label: 'login', path, status: error.status || null, message: error.message })
    }
  }

  if (process.env.BUDIBASE_API_KEY) {
    report.skipped.push({ label: 'login', message: 'Using BUDIBASE_API_KEY fallback' })
    return process.env.BUDIBASE_API_KEY
  }

  throw new Error('Unable to authenticate with Budibase. Set BUDIBASE_USER/BUDIBASE_PASSWORD or BUDIBASE_API_KEY.')
}

async function main() {
  const token = await login()
  const auth = { token }
  const app = await tryRequest('application', '/api/public/v1/applications', {
    ...auth,
    method: 'POST',
    body: JSON.stringify({ name: APP_NAME, url: '/', template: 'blank' }),
  }, true)
  const appId = app?._id || app?.id || app?.data?._id || app?.data?.id || process.env.BUDIBASE_APP_ID

  const datasource = await tryRequest('postgres-datasource', '/api/public/v1/datasources', {
    ...auth,
    method: 'POST',
    body: JSON.stringify({ name: 'Replay PostgreSQL', type: 'postgres', config: DB_CONFIG, appId }),
  }, true)
  const datasourceId = datasource?._id || datasource?.id || datasource?.data?._id || datasource?.data?.id || process.env.BUDIBASE_DATASOURCE_ID

  for (const name of [...editableTables, ...readOnlyTables, ...readOnlyViews]) {
    await tryRequest(`source:${name}`, '/api/public/v1/tables', {
      ...auth,
      method: 'POST',
      body: JSON.stringify({
        name,
        appId,
        datasourceId,
        type: readOnlyViews.includes(name) ? 'view' : 'table',
        schema: 'public',
        tableName: name,
        writable: editableTables.includes(name),
        readonly: !editableTables.includes(name),
      }),
    }, true)
  }

  for (const screen of screens) {
    await tryRequest(`screen:${screen.name}`, '/api/public/v1/screens', {
      ...auth,
      method: 'POST',
      body: JSON.stringify({ appId, ...screen, layout: 'minimal' }),
    }, true)
  }

  for (const endpoint of ['/api/run', '/api/suite', '/api/status/{{ runId }}']) {
    await tryRequest(`runner-query:${endpoint}`, '/api/public/v1/queries', {
      ...auth,
      method: 'POST',
      body: JSON.stringify({
        appId,
        name: `Runner ${endpoint}`,
        datasource: 'REST',
        method: endpoint.includes('status') ? 'GET' : 'POST',
        url: `http://playwright-runner:8550${endpoint}`,
      }),
    }, true)
  }

  console.log(JSON.stringify(report, null, 2))
}

main().catch(error => {
  console.error(JSON.stringify({ ...report, error: error.message }, null, 2))
  process.exit(1)
})
