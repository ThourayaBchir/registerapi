from celery import Celery

from app.core.config import get_settings

celery_app = Celery("user_activation")


def configure_celery() -> Celery:
    settings = get_settings()
    celery_app.conf.broker_url = settings.redis_url
    celery_app.conf.result_backend = settings.redis_url
    celery_app.autodiscover_tasks(["app.tasks"])
    return celery_app


configure_celery()
