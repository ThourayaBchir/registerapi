from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

celery_app = Celery("user_activation")


def configure_celery() -> Celery:
    settings = get_settings()
    celery_app.conf.update(
        broker_url=settings.redis_url,
        result_backend=settings.redis_url,
    )
    celery_app.autodiscover_tasks(["app.tasks"])
    return celery_app


configure_celery()


def get_celery_app() -> Celery:
    return celery_app
