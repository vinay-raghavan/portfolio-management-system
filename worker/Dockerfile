FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system -e .

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD celery -A worker.celery_app inspect ping -d celery@$HOSTNAME || exit 1

# Run Celery worker
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]

