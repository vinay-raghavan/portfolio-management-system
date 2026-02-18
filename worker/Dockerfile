# =============================================================================
# Stage 1: Builder - Compile dependencies with build tools
# =============================================================================
FROM python:3.14-slim AS builder

WORKDIR /app

# Install build tools for packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy shared package first (for dependency resolution)
COPY shared /shared

# Copy dependency files and README
COPY worker/pyproject.toml worker/README.md ./

# Copy application code
COPY worker/worker ./worker

# Install dependencies into virtual environment
# Remove asyncio backport package that shadows stdlib (pulled in by fyers-apiv3 via shared)
RUN uv sync --no-dev && \
    rm -rf /app/.venv/lib/python*/site-packages/asyncio* || true

# =============================================================================
# Stage 2a: Dev - For local development with shell access
# =============================================================================
FROM python:3.14-slim AS dev

WORKDIR /app

# Install uv for running commands
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy virtual environment and app from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/worker /app/worker
COPY --from=builder /shared /shared

# Copy pyproject.toml for uv to work
COPY worker/pyproject.toml worker/README.md ./

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD celery -A worker.celery_app inspect ping -d celery@$HOSTNAME || exit 1

CMD ["uv", "run", "celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]

# =============================================================================
# Stage 2b: Prod - Hardened image for production (no shell, minimal attack surface)
# =============================================================================
FROM cgr.dev/chainguard/python:latest AS prod

WORKDIR /app

# Copy virtual environment and app from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/worker /app/worker
COPY --from=builder /shared /shared

# Set environment variables for venv activation
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/.venv/lib/python3.14/site-packages:/app:/shared"
ENV PYTHONUNBUFFERED=1

# Note: No HEALTHCHECK in Chainguard (no curl/shell) - use orchestrator health checks
# Chainguard has ENTRYPOINT [/usr/bin/python], so CMD args are passed to python
CMD ["-m", "celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]

