FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build
FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 wget curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps
COPY backend/ /app/backend/
COPY --from=frontend-builder /app/frontend/dist/ /app/frontend/dist/
RUN mkdir -p /data/artifacts /data/seeds /data/backup
COPY data/seeds/ /data/seeds/
ENV PYTHONPATH=/app:/app/backend REPLAY_DATABASE_URL=/data/test.db REPLAY_ARTIFACTS_DIR=/data/artifacts REPLAY_SEEDS_DIR=/data/seeds
VOLUME /data
EXPOSE 8446
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD curl -f http://localhost:8446/api/v1/health || exit 1
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8446"]
