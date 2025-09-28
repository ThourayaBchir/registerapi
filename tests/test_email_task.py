from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from app.services.email import CeleryEmailService
from app.tasks import email as email_tasks


@pytest.mark.asyncio
async def test_celery_email_service_enqueues(mocker: MockerFixture) -> None:
    apply_async = mocker.patch("app.tasks.email.send_activation_email.apply_async")

    service = CeleryEmailService()
    await service.send_activation("user@example.com", "1234", 60)

    apply_async.assert_called_once()
    positional, keyword = apply_async.call_args
    actual_args = None
    queue = None
    if keyword and "args" in keyword:
        actual_args = keyword["args"]
        queue = keyword.get("queue")
    elif positional:
        last_positional = positional[-1]
        if isinstance(last_positional, dict) and "args" in last_positional:
            actual_args = last_positional["args"]
            queue = last_positional.get("queue")
    assert actual_args == ("user@example.com", "1234", 60)
    assert queue is None


def _prepare_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://register:register@postgres:5432/user_activation")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("EMAIL_API_URL", "https://email-api.example.com/v1/send")
    monkeypatch.setenv("SYSTEM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("SECRET_KEY", "secret")
    from app.core.config import get_settings

    get_settings.cache_clear()


def test_send_activation_email_success(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    _prepare_settings_env(monkeypatch)

    response = mocker.Mock(spec=httpx.Response)
    response.raise_for_status.return_value = None
    post = mocker.patch("httpx.post", return_value=response)

    retry = mocker.patch.object(email_tasks.send_activation_email, "retry", side_effect=AssertionError("retry should not be called"))

    email_tasks.send_activation_email.run("user@example.com", "1234", 60)

    post.assert_called_once()
    args, kwargs = post.call_args
    assert kwargs["json"]["to"] == "user@example.com"
    assert "1234" in kwargs["json"]["body"]
    retry.assert_not_called()


def test_send_activation_email_retries(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    _prepare_settings_env(monkeypatch)

    mocker.patch("httpx.post", side_effect=httpx.HTTPError("boom"))

    retry = mocker.patch.object(email_tasks.send_activation_email, "retry", side_effect=RuntimeError("retry"))

    with pytest.raises(RuntimeError):
        email_tasks.send_activation_email.run("user@example.com", "1234", 60)

    assert retry.call_count >= 1
    first_call = retry.call_args_list[0]
    assert isinstance(first_call.kwargs.get("exc"), httpx.HTTPError)
