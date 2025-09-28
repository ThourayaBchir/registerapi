from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "user_activation",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
)

celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    task_default_queue="default",
)

celery_app.autodiscover_tasks(["app"])


__all__ = ["celery_app"]
