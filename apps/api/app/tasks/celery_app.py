from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "lexagent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.contract_tasks",
        "app.tasks.reminder_tasks",
        "app.tasks.document_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "check-reminders-hourly": {
        "task": "app.tasks.reminder_tasks.check_and_send_reminders",
        "schedule": crontab(minute=0),  # Every hour
    },
    "check-overdue-daily": {
        "task": "app.tasks.reminder_tasks.check_overdue_obligations",
        "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM UTC
    },
    "send-signature-reminders": {
        "task": "app.tasks.document_tasks.check_pending_signatures",
        "schedule": crontab(hour=9, minute=0),  # Daily at 9 AM UTC
    },
}
