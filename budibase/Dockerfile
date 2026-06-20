FROM node:20-alpine
WORKDIR /app
RUN apk add --no-cache curl
COPY setup-app.js setup-app.sh ./
CMD ["node", "setup-app.js"]
