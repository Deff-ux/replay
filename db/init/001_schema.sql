CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS test_cases (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(255) NOT NULL,
  product VARCHAR(50) NOT NULL CHECK (product IN ('neo', 'payroll', 'ta', 'finance', 'bns', 'veera')),
  module VARCHAR(100),
  tags TEXT[] DEFAULT ARRAY[]::TEXT[],
  steps JSONB NOT NULL DEFAULT '[]'::jsonb,
  assertions JSONB DEFAULT '[]'::jsonb,
  status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  created_by VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tc_product ON test_cases(product);
CREATE INDEX IF NOT EXISTS idx_tc_status ON test_cases(status);
CREATE INDEX IF NOT EXISTS idx_tc_tags ON test_cases USING GIN(tags);

CREATE TABLE IF NOT EXISTS suites (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(255) NOT NULL,
  product VARCHAR(50) CHECK (product IS NULL OR product IN ('neo', 'payroll', 'ta', 'finance', 'bns', 'veera')),
  test_case_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
  schedule_cron VARCHAR(100),
  schedule_enabled BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_suites_product ON suites(product);
CREATE INDEX IF NOT EXISTS idx_suites_schedule_enabled ON suites(schedule_enabled);

CREATE TABLE IF NOT EXISTS test_runs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  run_id VARCHAR(100) UNIQUE NOT NULL,
  suite_id UUID REFERENCES suites(id),
  test_case_id UUID REFERENCES test_cases(id),
  status VARCHAR(20) DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'interrupted')),
  progress INT DEFAULT 0,
  total INT DEFAULT 0,
  passed INT DEFAULT 0,
  failed INT DEFAULT 0,
  duration_seconds INT,
  environment VARCHAR(20) CHECK (environment IS NULL OR environment IN ('staging', 'production', 'dev')),
  triggered_by VARCHAR(20) DEFAULT 'manual',
  result JSONB DEFAULT '{}'::jsonb,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tr_status ON test_runs(status);
CREATE INDEX IF NOT EXISTS idx_tr_created ON test_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tr_suite ON test_runs(suite_id);

CREATE TABLE IF NOT EXISTS environments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name VARCHAR(50) UNIQUE NOT NULL CHECK (name IN ('staging', 'production', 'dev')),
  base_url VARCHAR(255) NOT NULL,
  auth_type VARCHAR(20) DEFAULT 'none' CHECK (auth_type IN ('none', 'basic', 'apikey')),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS artifact_cleanup_log (
  id SERIAL PRIMARY KEY,
  run_at TIMESTAMP DEFAULT NOW(),
  files_deleted INT DEFAULT 0,
  space_freed_bytes BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS activity_log (
  id SERIAL PRIMARY KEY,
  actor VARCHAR(100),
  action VARCHAR(50) NOT NULL,
  target_type VARCHAR(50),
  target_id VARCHAR(100),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_al_created ON activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_al_action ON activity_log(action);
