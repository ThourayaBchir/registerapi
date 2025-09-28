from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.utils.email import render_activation_email

_LOGGER = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="send_activation_email",
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
    autoretry_for=(Exception,),
)
def send_activation_email(self, email: str, code: str, ttl_seconds: int) -> None:
    settings = get_settings()
    subject, body = render_activation_email(code, ttl_seconds)

    payload: dict[str, Any] = {
        "from": settings.system_email,
        "to": email,
        "subject": subject,
        "body": body,
    }

    try:
        response = httpx.post(
            settings.email_api_url,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        _LOGGER.info("Activation email dispatched via API", extra={"to": email})
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Activation email send failed, retrying", exc_info=exc)
        raise self.retry(exc=exc)
