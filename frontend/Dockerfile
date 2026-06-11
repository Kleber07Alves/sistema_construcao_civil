FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
# npm ci é determinístico e usa package-lock.json — mais confiável que npm install
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# URL da API injetada em tempo de build — baked no bundle estático
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Telemetria Next.js desativada no CI/build
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# PORT e HOSTNAME lidos pelo standalone server.js
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Copiar apenas o bundle compilado — sem node_modules completo (~200 MB vs ~800 MB)
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static     ./.next/static
# Copiar pasta public/ se existir (assets estáticos como favicon, imagens)
COPY --from=builder /app/public           ./public 2>/dev/null || true

EXPOSE 3000

# server.js é gerado pelo output standalone do Next.js
CMD ["node", "server.js"]