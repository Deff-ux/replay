# Rencana Pengembangan Baru — PHIRO WebUI Test Dashboard

## Status Implementasi

Status per 20 Juni 2026: MVP foundation dan kewajiban Minggu 2 sudah tersedia di repo. Stack Docker, schema PostgreSQL, Runner API, artifact screenshot/video, notifikasi Telegram saat failure, scheduled suite execution, script backup/cleanup, dan blueprint Budibase terdokumentasi. Item Nice to Have tetap opsional.

## Ringkasan MVP

Dashboard regresi Playwright untuk 6 produk PHIRO (`neo`, `payroll`, `ta`, `finance`, `bns`, `veera`) dengan UI Budibase, database PostgreSQL, runner Playwright berbasis Node.js, artifact screenshot/video, dan notifikasi Telegram saat failure.

**Target MVP:** 2 minggu  
**VPS target:** `xbata-mm84` — Ubuntu 24.04, 4 vCPU, 7.8 GB RAM, 58 GB disk  
**Domain:** `test.defrinogionaldo.com` via Cloudflare Tunnel ke `localhost:8446`

## Arsitektur Final

```text
Cloudflare Tunnel
  → Budibase :8446
      → PostgreSQL :5432
      → Playwright Runner API :8550 (internal only)
          → /artifacts screenshot + video
          → Telegram Bot API on failed runs
```

## Fase 1 — Foundation (Minggu 1)

### 1. Infrastruktur Docker

- Jalankan `budibase/budibase:latest` pada `127.0.0.1:8446`.
- Jalankan `postgres:16-alpine` dengan health check.
- Jalankan `playwright-runner` internal pada port `8550`.
- Gunakan volume persisten:
  - `budibase_data`
  - `pg_data`
  - `test_data`
  - `test_artifacts`

### 2. Database & Schema

- Terapkan schema PostgreSQL dari `db/init/001_schema.sql`.
- Wajib ada index untuk filter utama: produk, status, tags, created_at.
- Semua secret harus masuk via `.env`, bukan hardcoded.

### 3. Playwright Runner API

Endpoint MVP:

| Method | Endpoint | Fungsi |
| --- | --- | --- |
| `GET` | `/api/health` | Health check DB, artifact dir, uptime |
| `POST` | `/api/run` | Queue single test case |
| `POST` | `/api/suite` | Queue suite dengan max 3 worker |
| `GET` | `/api/status/:runId` | Polling status run |

Requirement teknis:

- Structured JSON logging dengan Winston.
- DB pool max 5 connection.
- Rate limit 1 request/detik/IP.
- IP allowlist untuk localhost dan network Docker.
- Browser cleanup di `finally`.
- Graceful shutdown menandai run `running` menjadi `interrupted`.

### 4. Cloudflare Tunnel

Konfigurasi public hostname:

- Subdomain: `test`
- Domain: `defrinogionaldo.com`
- Service: `http://localhost:8446`

## Fase 2 — Budibase App (Minggu 1-2)

### Screens Wajib

| Screen | Data Source | Fitur MVP |
| --- | --- | --- |
| Dashboard | `test_runs` aggregated | Kartu status produk, pass rate, queue length |
| Test Cases | `test_cases` | List, search, filter produk/status/tags |
| Test Detail | `test_cases`, `test_runs` | Edit steps/assertions dan histori run |
| Suite Builder | `suites`, `test_cases` | Susun ordered test case IDs |
| Suite Run | Runner API | Tombol run, progress, polling status |
| Run Results | `test_runs` | Filter pass/fail, export |
| Run Detail | `test_runs`, artifacts | Screenshot, video, log |
| Environment | `environments` | CRUD URL staging/production/dev |
| Schedule | `suites` | Enable cron per suite |

### Jadwal Default

- Full regression: Minggu 23:00.
- Smoke test: setiap hari 06:00 dan 18:00.
- Artifact cleanup: harian 03:00.
- DB backup: harian, retensi 7 hari.
- Disk monitor: tiap jam, alert Telegram jika penggunaan >80%.

## Checklist Non-Fungsional

### Keamanan

- Cloudflare Tunnel only; tidak expose port langsung ke internet.
- Runner hanya listen di `127.0.0.1` dalam container dan port tidak dipublish ke host.
- Semua token/password via `.env`.
- Screenshot redaction sebelum artifact disimpan.
- Budibase auth dan role-based access wajib aktif.
- Audit trail ke `activity_log`.

### Reliability & Recovery

- `restart: unless-stopped` untuk semua service.
- Health check service.
- `SIGTERM` graceful shutdown.
- Retry 1x untuk failure tipe timeout.
- Telegram notification circuit breaker 1 menit.
- Backup DB harian.
- Cleanup artifact sesuai `ARTIFACT_RETENTION_DAYS`.

### Performa

- Max 3 browser concurrent via `MAX_PARALLEL_WORKERS`.
- Execution async; API langsung return queued.
- Suite besar diproses dalam chunk.
- Index PostgreSQL untuk query Budibase.

## Migrasi dari Codebase Lama

Codebase lama FastAPI + Vue tetap dipertahankan sebagai referensi legacy, tetapi target deployment baru adalah stack Budibase + PostgreSQL + Node Playwright Runner. File deployment utama sekarang berada di:

- `docker/docker-compose.yml`
- `playwright-runner/`
- `db/init/001_schema.sql`
- `scripts/cleanup-artifacts.sh`
- `scripts/backup-db.sh`
- `scripts/systemd/testdashboard.service`

## Prioritas Implementasi

### Wajib Minggu 1

- [x] Docker Compose final di `docker/docker-compose.yml`.
- [x] PostgreSQL schema + indexes di `db/init/001_schema.sql`.
- [x] Runner API + health check di `playwright-runner/index.js`.
- [x] Cloudflare Tunnel via service `cloudflared` profile `tunnel`.
- [x] Budibase screens dasar terdokumentasi di `budibase/README.md`.

### Wajib Minggu 2

- [x] Parallel suite execution dengan batas `MAX_PARALLEL_WORKERS` maksimal 3.
- [x] Telegram notification hanya saat failure dan dilindungi circuit breaker 1 menit.
- [x] Scheduled execution untuk suite aktif berdasarkan `schedule_cron`.
- [x] Screenshot/video artifacts dan registry metadata `artifact_files`.
- [x] Graceful shutdown menandai run `running` menjadi `interrupted`.

### Nice to Have

- GitHub Actions CI/CD.
- OpenProject auto issue.
- Visual diff.
- Multi-browser.
- Advanced user management.
