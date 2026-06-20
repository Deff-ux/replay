# PHIRO WebUI Test Dashboard

Replay sekarang diarahkan menjadi **Custom WebUI Test Dashboard** untuk regresi Playwright PHIRO dengan stack final:

- Budibase untuk UI dashboard.
- PostgreSQL untuk data test case, suite, run history, environment, dan audit log.
- Node.js Playwright Runner untuk eksekusi test, screenshot/video artifact, dan Telegram alert.
- Docker Compose untuk deployment VPS `xbata-mm84`.

Rencana pengembangan lengkap ada di [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md).

## Quick Start Deployment

```bash
cp .env.example .env
# isi DB_PASSWORD, JWT_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
cd docker
docker compose up -d --build
# optional: jalankan tunnel terkelola Cloudflare jika CLOUDFLARE_TUNNEL_TOKEN sudah diisi
docker compose --profile tunnel up -d cloudflared
```

Akses Budibase melalui Cloudflare Tunnel:

```text
test.defrinogionaldo.com → http://localhost:8446
```

## File Utama

| Path | Fungsi |
| --- | --- |
| `docker/docker-compose.yml` | Stack Budibase + PostgreSQL + Playwright Runner |
| `db/init/001_schema.sql` | Schema PostgreSQL dan index untuk MVP |
| `playwright-runner/` | Express API runner Playwright |
| `scripts/cleanup-artifacts.sh` | Cleanup artifact + disk alert Telegram |
| `scripts/backup-db.sh` | Backup PostgreSQL harian |
| `scripts/systemd/testdashboard.service` | Unit systemd alternatif |

## Runner API

| Method | Endpoint | Fungsi |
| --- | --- | --- |
| `GET` | `/api/health` | Health check DB, artifact directory, dan uptime |
| `POST` | `/api/run` | Queue single test case |
| `POST` | `/api/suite` | Queue suite dengan maksimal 3 worker |
| `GET` | `/api/status/:runId` | Polling status run |

## Legacy App

Kode FastAPI + Vue lama masih ada di `backend/` dan `frontend/` sebagai referensi migrasi, tetapi bukan target deployment MVP baru.
