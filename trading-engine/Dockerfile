FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
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

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the application
CMD ["uv", "run", "uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8001"]

