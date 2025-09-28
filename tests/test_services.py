from __future__ import annotations

import pytest
import pytest_asyncio
from pydantic import ValidationError
from pytest_mock import MockerFixture

from app.core.config import Settings
from app.repositories.activation import ActivationRepository
from app.repositories.user import UserRepository
from app.services.user import (
    ActivationResult,
    UserAlreadyActiveError,
    UserNotFoundError,
    UserPendingActivationError,
    UserService,
)


def test_user_create_password_strips_spaces() -> None:
    from app.models.user import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(email="space@example.com", password=" secret ")


def test_user_create_password_min_length() -> None:
    from app.models.user import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(email="short@example.com", password="short")


def test_user_create_valid_payload() -> None:
    from app.models.user import UserCreate

    payload = UserCreate(email="john@example.com", password="LongEnough1")
    assert payload.email == "john@example.com"


@pytest_asyncio.fixture
async def service_components(mocker: MockerFixture, db_conn):
    users = UserRepository(db_conn)
    codes = ActivationRepository(db_conn)
    email_service = mocker.Mock()
    email_service.send_activation = mocker.AsyncMock()
    settings = Settings(
        database_url="postgresql://register:register@postgres:5432/user_activation",
        redis_url="redis://redis:6379/0",
        smtp_host="mail",
        secret_key="secret",
        activation_code_ttl_seconds=60,
    )
    service = UserService(users, codes, email_service, settings)
    return service, email_service, users, codes


@pytest.mark.asyncio
async def test_register_and_activate_flow(service_components):
    service, email_service, users, _ = service_components

    result = await service.register("flow@example.com", "Passw0rd!1")

    assert isinstance(result, ActivationResult)
    email_service.send_activation.assert_awaited_once()

    user = await users.get_user_by_email("flow@example.com")
    assert user is not None and user["is_active"] is False

    activated = await service.activate("flow@example.com", result.code)
    assert activated is True

    user = await users.get_user_by_email("flow@example.com")
    assert user["is_active"] is True

    assert await service.activate("flow@example.com", result.code) is False


@pytest.mark.asyncio
async def test_register_existing_pending_user_raises(service_components):
    service, _, _, _ = service_components

    await service.register("pending@example.com", "Passw0rd!1")

    with pytest.raises(UserPendingActivationError):
        await service.register("pending@example.com", "AnotherPass1")


@pytest.mark.asyncio
async def test_register_existing_active_user_raises(service_components):
    service, _, users, _ = service_components

    registration = await service.register("active@example.com", "Passw0rd!1")
    await service.activate("active@example.com", registration.code)

    with pytest.raises(UserAlreadyActiveError):
        await service.register("active@example.com", "NewPass123")

    user = await users.get_user_by_email("active@example.com")
    assert user["is_active"] is True


@pytest.mark.asyncio
async def test_request_activation_code_flow(service_components):
    service, email_service, _, codes = service_components

    await service.register("resend@example.com", "Passw0rd!1")

    email_service.send_activation.reset_mock()
    result = await service.request_activation_code("resend@example.com")

    email_service.send_activation.assert_awaited_once()
    assert isinstance(result, ActivationResult)

    latest = await codes.latest_code("resend@example.com")
    assert latest is not None


@pytest.mark.asyncio
async def test_request_activation_code_nonexistent(service_components):
    service, _, _, _ = service_components

    with pytest.raises(UserNotFoundError):
        await service.request_activation_code("missing@example.com")


@pytest.mark.asyncio
async def test_request_activation_code_active_user(service_components):
    service, _, _, _ = service_components

    activation = await service.register("done@example.com", "Passw0rd!1")
    await service.activate("done@example.com", activation.code)

    with pytest.raises(UserAlreadyActiveError):
        await service.request_activation_code("done@example.com")


@pytest.mark.asyncio
async def test_activation_fails_with_wrong_code(service_components):
    service, _, _, _ = service_components

    await service.register("wrong-code@example.com", "Passw0rd!1")
    result = await service.activate("wrong-code@example.com", "9999")
    assert result is False
