# =============================================================================
# Stage 1: Builder - Compile dependencies with build tools
# =============================================================================
FROM python:3.13-slim AS builder

# Install build tools for packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy shared package first (for dependency resolution)
COPY shared /shared

# Copy dependency files
COPY trading-engine/pyproject.toml ./

# Install dependencies (including shared package)
RUN uv sync --no-dev --no-install-project

# Copy application code
COPY trading-engine/ .

# Install the project
RUN uv sync --no-dev

# =============================================================================
# Stage 2a: Dev - For local development with shell access
# =============================================================================
FROM python:3.13-slim AS dev

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for running commands
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy virtual environment and app from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/engine /app/engine
COPY --from=builder /shared /shared

# Copy pyproject.toml and README.md for uv/hatchling to work
COPY trading-engine/pyproject.toml trading-engine/README.md ./

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uv", "run", "uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8001"]

# =============================================================================
# Stage 2b: Prod - Hardened image for production (no shell, minimal attack surface)
# =============================================================================
FROM cgr.dev/chainguard/python:latest AS prod

WORKDIR /app

# Copy virtual environment and app from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/engine /app/engine
COPY --from=builder /shared /shared

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

# Note: No HEALTHCHECK in Chainguard (no curl/shell) - use orchestrator health checks
CMD ["python", "-m", "uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8001"]

