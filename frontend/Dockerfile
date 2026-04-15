FROM node:20-alpine AS base

# Install dependencies
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

# Build
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build-time arguments for Next.js public env vars
# These MUST be declared as ARG so docker build --build-arg works.
# Defaults are production-safe (empty API URL = relative URLs, no CORS).
ARG NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_ENABLE_MOCKS="false"
ARG NEXT_PUBLIC_ALGORAND_NETWORK="testnet"
ARG NEXT_PUBLIC_ALGOD_SERVER="https://testnet-api.4160.nodely.dev"
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_ENABLE_MOCKS=${NEXT_PUBLIC_ENABLE_MOCKS}
ENV NEXT_PUBLIC_ALGORAND_NETWORK=${NEXT_PUBLIC_ALGORAND_NETWORK}
ENV NEXT_PUBLIC_ALGOD_SERVER=${NEXT_PUBLIC_ALGOD_SERVER}
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# Production runner
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
