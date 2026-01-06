FROM python:3.13-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

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

# Install dependencies
RUN uv sync --no-dev

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

