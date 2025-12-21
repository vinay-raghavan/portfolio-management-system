# Portfolio Worker

Celery worker for background tasks in the Portfolio Management System.

## Tasks

- Price updates
- Instrument sync
- Signal generation
- Notifications

## Running

```bash
# Worker
celery -A worker.celery_app worker --loglevel=info

# Beat scheduler
celery -A worker.celery_app beat --loglevel=info
```

