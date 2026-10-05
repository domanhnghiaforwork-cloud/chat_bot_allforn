# syntax=docker/dockerfile:1.7

FROM node:24-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci


FROM node:24-alpine AS builder

ARG BACKEND_URL=http://backend:8000
ARG NEXT_PUBLIC_ASYNC_CHAT_ENABLED=true
ARG NEXT_PUBLIC_BASE_PATH=

ENV NEXT_TELEMETRY_DISABLED=1 \
    BACKEND_URL=${BACKEND_URL} \
    NEXT_PUBLIC_ASYNC_CHAT_ENABLED=${NEXT_PUBLIC_ASYNC_CHAT_ENABLED} \
    NEXT_PUBLIC_BASE_PATH=${NEXT_PUBLIC_BASE_PATH}

WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build


FROM node:24-alpine AS runtime

ARG NEXT_PUBLIC_BASE_PATH=

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    BACKEND_URL=http://backend:8000 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    NEXT_PUBLIC_BASE_PATH=${NEXT_PUBLIC_BASE_PATH}

WORKDIR /app

COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
COPY --from=builder --chown=node:node /app/public ./public

USER node

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000' + (process.env.NEXT_PUBLIC_BASE_PATH || '') + '/api/health/live').then(r => { if (!r.ok) process.exit(1) }).catch(() => process.exit(1))"]

CMD ["node", "server.js"]
