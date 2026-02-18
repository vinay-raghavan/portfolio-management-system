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

# Copy dependency files and README (required by pyproject.toml)
COPY backend/pyproject.toml backend/README.md ./

# Copy application code (needed for editable install)
COPY backend/app ./app

# Copy Alembic configuration and migrations
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic

# Install dependencies into virtual environment
# Remove asyncio backport package that shadows stdlib (pulled in by fyers-apiv3)
RUN uv sync --no-dev && \
    rm -rf /app/.venv/lib/python*/site-packages/asyncio* || true

# =============================================================================
# Stage 2a: Dev - For local development with shell access
# =============================================================================
FROM python:3.14-slim AS dev

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for running commands
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy virtual environment and app from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/alembic.ini /app/alembic.ini
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /shared /shared

# Copy pyproject.toml for uv to work
COPY backend/pyproject.toml backend/README.md ./

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Stage 2b: Prod - Hardened image for production (no shell, minimal attack surface)
# =============================================================================
FROM cgr.dev/chainguard/python:latest AS prod

WORKDIR /app

# Copy virtual environment and app from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/alembic.ini /app/alembic.ini
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /shared /shared

# Set environment variables for venv activation
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/.venv/lib/python3.14/site-packages:/app:/shared"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Note: No HEALTHCHECK in Chainguard (no curl/shell) - use orchestrator health checks
# Chainguard has ENTRYPOINT [/usr/bin/python], so CMD args are passed to python
CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

