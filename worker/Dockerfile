FROM python:3.13-slim

WORKDIR /app

# Install build tools for packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files and README
COPY pyproject.toml README.md ./

# Install dependencies
RUN uv pip install --system -e .

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD celery -A worker.celery_app inspect ping -d celery@$HOSTNAME || exit 1

# Run Celery worker
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]

