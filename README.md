# Replay

Replay is a single-image FastAPI + Vue 3 + SQLite + Playwright regression dashboard.

## Development

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8446
npm --prefix frontend install
npm --prefix frontend run dev
```

## Docker

```bash
docker build -t replay:latest -f docker/Dockerfile .
docker run -p 8446:8446 -v replay-data:/data -e REPLAY_SECRET_KEY=$(openssl rand -hex 32) replay:latest
```
