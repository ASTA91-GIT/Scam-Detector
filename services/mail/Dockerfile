# ScamGuard AI - Node.js Mail Service Dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./

RUN npm ci --only=production

COPY server.js ./
COPY src/ ./src/

ENV NODE_ENV=production \
    MAIL_PORT=5001

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:5001/health || exit 1

USER node

CMD ["node", "server.js"]
