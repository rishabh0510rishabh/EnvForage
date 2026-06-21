# 1. Install dependencies only when needed
FROM node:22-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install dependencies based on the package.json
COPY package.json package-lock.json* ./
RUN npm ci

# 2. Rebuild the source code only when needed
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Disable Next.js telemetry during the build phase
ENV NEXT_TELEMETRY_DISABLED=1

# Build-time ARG: public API URL (used by frontend fetch calls)
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Build-time ARG: internal backend URL used by next.config.ts rewrites()
# Must be passed at build time — rewrites() runs during `npm run build`, not at runtime
ARG BACKEND_API_URL
ENV BACKEND_API_URL=${BACKEND_API_URL}

RUN npm run build

# 3. Production runner image
FROM node:22-alpine AS runner
WORKDIR /app

RUN apk update && apk upgrade --no-cache && npm install -g npm@latest

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy static assets and public folder
COPY --from=builder /app/public ./public

# Set permissions for prerendering cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Leverage output standalone to copy only tracing dependencies
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
