# =============================================================================
# AIMS-System Web Server Dockerfile (Multi-Stage Build)
# Base: Node.js 18 Alpine
# =============================================================================

# ============ STAGE 1: Builder ============
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files for dependency caching
COPY web/package.json web/package-lock.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# ============ STAGE 2: Runtime ============
FROM node:18-alpine AS runtime

WORKDIR /app

# Install production dependencies only
COPY web/package.json web/package-lock.json ./
RUN npm ci --omit=dev && \
    npm cache clean --force

# Copy application source
COPY web/ ./

# Remove dev files not needed in production
RUN rm -f .gitignore

EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3001/ || exit 1

CMD ["node", "app.js"]
