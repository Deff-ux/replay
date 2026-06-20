FROM node:20-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev \
  && npx playwright install --with-deps chromium
COPY index.js ./

RUN mkdir -p /artifacts /data /var/log/testdashboard \
  && chown -R node:node /app /artifacts /data /var/log/testdashboard

USER node
EXPOSE 8550
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://127.0.0.1:8550/api/health || exit 1
CMD ["node", "index.js"]
