from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "user_activation",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
)

celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    task_default_queue="default",
)

celery_app.autodiscover_tasks(["app.tasks"])


__all__ = ["celery_app"]
