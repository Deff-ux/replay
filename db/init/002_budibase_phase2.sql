-- Phase 2 Budibase support objects: dashboard aggregations, runner payload views,
-- default schedules, and artifact metadata exposed as queryable JSON for Budibase.

CREATE TABLE IF NOT EXISTS artifact_files (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id VARCHAR(100) NOT NULL REFERENCES test_runs(run_id) ON DELETE CASCADE,
  test_case_id UUID REFERENCES test_cases(id),
  artifact_type VARCHAR(20) NOT NULL CHECK (artifact_type IN ('screenshot', 'video', 'log')),
  file_path TEXT NOT NULL,
  public_path TEXT NOT NULL,
  file_size_bytes BIGINT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_artifact_files_run ON artifact_files(run_id, artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifact_files_case ON artifact_files(test_case_id);
CREATE INDEX IF NOT EXISTS idx_artifact_files_created ON artifact_files(created_at DESC);

ALTER TABLE suites ADD COLUMN IF NOT EXISTS suite_type VARCHAR(20) DEFAULT 'custom' CHECK (suite_type IN ('custom', 'smoke', 'regression'));
ALTER TABLE suites ADD COLUMN IF NOT EXISTS schedule_label VARCHAR(100);
CREATE INDEX IF NOT EXISTS idx_suites_type ON suites(suite_type);

CREATE OR REPLACE VIEW budibase_dashboard_product_cards AS
SELECT
  product,
  COUNT(*) FILTER (WHERE status = 'active') AS active_cases,
  COUNT(*) FILTER (WHERE status = 'archived') AS archived_cases,
  COALESCE(ROUND(100.0 * SUM(passed) / NULLIF(SUM(passed + failed), 0), 2), 0) AS pass_rate,
  COUNT(DISTINCT run_id) FILTER (WHERE run_status IN ('queued', 'running')) AS queue_length,
  MAX(last_run_at) AS last_run_at
FROM (
  SELECT
    tc.product,
    tc.status,
    tr.run_id,
    tr.status AS run_status,
    tr.passed,
    tr.failed,
    tr.created_at AS last_run_at
  FROM test_cases tc
  LEFT JOIN test_runs tr ON tr.test_case_id = tc.id
  UNION ALL
  SELECT
    s.product,
    'active' AS status,
    tr.run_id,
    tr.status AS run_status,
    tr.passed,
    tr.failed,
    tr.created_at AS last_run_at
  FROM suites s
  JOIN test_runs tr ON tr.suite_id = s.id
  WHERE s.product IS NOT NULL
) x
WHERE product IS NOT NULL
GROUP BY product;

CREATE OR REPLACE VIEW budibase_dashboard_summary AS
SELECT
  COUNT(*) FILTER (WHERE status = 'queued') AS queued_runs,
  COUNT(*) FILTER (WHERE status = 'running') AS running_runs,
  COUNT(*) FILTER (WHERE status = 'completed') AS completed_runs,
  COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
  COALESCE(ROUND(100.0 * SUM(passed) / NULLIF(SUM(passed + failed), 0), 2), 0) AS overall_pass_rate,
  COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours') AS runs_last_24h
FROM test_runs;

CREATE OR REPLACE VIEW budibase_test_case_list AS
SELECT
  tc.id,
  tc.name,
  tc.product,
  tc.module,
  tc.tags,
  tc.status,
  tc.updated_at,
  COUNT(tr.id) AS run_count,
  MAX(tr.created_at) AS last_run_at,
  (ARRAY_AGG(tr.status ORDER BY tr.created_at DESC))[1] AS last_run_status
FROM test_cases tc
LEFT JOIN test_runs tr ON tr.test_case_id = tc.id
GROUP BY tc.id;

CREATE OR REPLACE VIEW budibase_run_results AS
SELECT
  tr.id,
  tr.run_id,
  COALESCE(tc.product, s.product) AS product,
  COALESCE(tc.name, s.name) AS target_name,
  CASE WHEN tr.suite_id IS NULL THEN 'test_case' ELSE 'suite' END AS target_type,
  tr.status,
  tr.progress,
  tr.total,
  tr.passed,
  tr.failed,
  tr.environment,
  tr.triggered_by,
  tr.duration_seconds,
  tr.created_at,
  tr.started_at,
  tr.finished_at
FROM test_runs tr
LEFT JOIN test_cases tc ON tc.id = tr.test_case_id
LEFT JOIN suites s ON s.id = tr.suite_id;

CREATE OR REPLACE VIEW budibase_run_detail AS
SELECT
  tr.*,
  COALESCE(
    jsonb_agg(
      jsonb_build_object(
        'type', af.artifact_type,
        'path', af.public_path,
        'size', af.file_size_bytes,
        'createdAt', af.created_at
      ) ORDER BY af.created_at
    ) FILTER (WHERE af.id IS NOT NULL),
    '[]'::jsonb
  ) AS artifacts
FROM test_runs tr
LEFT JOIN artifact_files af ON af.run_id = tr.run_id
GROUP BY tr.id;

INSERT INTO suites (name, product, test_case_ids, schedule_cron, schedule_enabled, suite_type, schedule_label)
VALUES
  ('Full regression', NULL, ARRAY[]::UUID[], '0 23 * * 0', false, 'regression', 'Minggu 23:00'),
  ('Smoke test', NULL, ARRAY[]::UUID[], '0 6,18 * * *', false, 'smoke', 'Setiap hari 06:00 dan 18:00')
ON CONFLICT DO NOTHING;
