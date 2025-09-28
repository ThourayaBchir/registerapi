from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from app.services.email import CeleryEmailService
from app.tasks import email as email_tasks


@pytest.mark.asyncio
async def test_celery_email_service_enqueues(mocker: MockerFixture) -> None:
    delay = mocker.patch("app.tasks.email.send_activation_email.delay")

    service = CeleryEmailService()
    await service.send_activation("user@example.com", "1234", 60)

    delay.assert_called_once_with("user@example.com", "1234", 60)


def test_send_activation_email_success(settings_env, mocker: MockerFixture) -> None:
    response = mocker.Mock(spec=httpx.Response)
    response.raise_for_status.return_value = None
    post = mocker.patch("httpx.post", return_value=response)

    retry = mocker.patch.object(
        email_tasks.send_activation_email,
        "retry",
        side_effect=AssertionError("retry should not be called"),
    )

    email_tasks.send_activation_email.run("user@example.com", "1234", 60)

    post.assert_called_once()
    args, kwargs = post.call_args
    assert kwargs["json"]["to"] == "user@example.com"
    assert "1234" in kwargs["json"]["body"]
    retry.assert_not_called()


def test_send_activation_email_retries(settings_env, mocker: MockerFixture) -> None:
    mocker.patch("httpx.post", side_effect=httpx.HTTPError("boom"))

    retry = mocker.patch.object(
        email_tasks.send_activation_email, "retry", side_effect=RuntimeError("retry")
    )

    with pytest.raises(RuntimeError):
        email_tasks.send_activation_email.run("user@example.com", "1234", 60)

    assert retry.call_count >= 1
    first_call = retry.call_args_list[0]
    assert isinstance(first_call.kwargs.get("exc"), httpx.HTTPError)
