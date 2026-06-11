

# ── Stage 1: instalar dependências ──────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# ── Stage 2: build da aplicação ─────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# URL da API baked no bundle estático em tempo de build
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1

RUN mkdir -p public

ENV NODE_OPTIONS="--max-old-space-size=2048"

RUN npm run build

# ── Stage 3: runtime mínimo (usa output: standalone do next.config.mjs) ─────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Copia o bundle autossuficiente gerado pelo output: standalone
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static     ./.next/static

COPY --from=builder /app/public           ./public

EXPOSE 3000

# server.js é gerado automaticamente pelo output: standalone do Next.js
CMD ["node", "server.js"]