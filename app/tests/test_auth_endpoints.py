from __future__ import annotations

import os

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient, BasicAuth

from app.api.deps import get_db_connection, get_rate_limiter, get_user_service
from app.core.config import get_settings
from app.main import app
from app.repositories.activation import ActivationRepository
from app.repositories.user import UserRepository
from app.services.email import EmailService
from app.services.user import UserService
from app.services.rate_limiter import RateLimitExceeded


class StubEmailService(EmailService):
    def __init__(self) -> None:
        self.sent_codes: dict[str, str] = {}

    async def send_activation(self, email: str, code: str, ttl_seconds: int) -> None:
        self.sent_codes[email] = code


class MemoryRateLimiter:
    """Test double mirroring the behaviour of the Redis-backed limiter."""

    def __init__(
        self, max_activation_attempts: int = 5, per_minute_resend: int = 1, daily_resend: int = 5
    ) -> None:
        self.max_activation_attempts = max_activation_attempts
        self.per_minute_resend = per_minute_resend
        self.daily_resend = daily_resend
        self.activation_failures: dict[str, int] = {}
        self.locked: set[str] = set()
        self.minute_resends: dict[str, int] = {}
        self.daily_resends: dict[str, int] = {}

    async def ensure_activation_allowed(self, email: str) -> None:
        if email in self.locked:
            raise RateLimitExceeded("Too many activation attempts.")

    async def record_activation_failure(self, email: str) -> None:
        count = self.activation_failures.get(email, 0) + 1
        self.activation_failures[email] = count
        if count >= self.max_activation_attempts:
            self.locked.add(email)

    async def reset_activation(self, email: str) -> None:
        self.activation_failures.pop(email, None)
        self.locked.discard(email)

    async def ensure_resend_allowed(self, email: str) -> None:
        if self.minute_resends.get(email, 0) >= self.per_minute_resend:
            raise RateLimitExceeded("Too many resend requests.")
        if self.daily_resends.get(email, 0) >= self.daily_resend:
            raise RateLimitExceeded("Daily resend limit reached.")

    async def record_resend(self, email: str) -> None:
        self.minute_resends[email] = self.minute_resends.get(email, 0) + 1
        self.daily_resends[email] = self.daily_resends.get(email, 0) + 1


@pytest_asyncio.fixture
async def api_client(db_conn, monkeypatch: pytest.MonkeyPatch, settings_env):
    monkeypatch.setenv(
        "DATABASE_URL",
        os.getenv(
            "TEST_DATABASE_URL", "postgresql://register:register@postgres:5432/user_activation"
        ),
    )

    get_settings.cache_clear()  # type: ignore[attr-defined]

    email_service = StubEmailService()
    user_repo = UserRepository(db_conn)
    activation_repo = ActivationRepository(db_conn)
    settings = get_settings()
    service = UserService(user_repo, activation_repo, email_service, settings)
    rate_limiter = MemoryRateLimiter(max_activation_attempts=2, per_minute_resend=1, daily_resend=2)

    async def _get_db_connection_override():
        yield db_conn

    async def _get_user_service_override():
        return service

    app.dependency_overrides[get_db_connection] = _get_db_connection_override
    app.dependency_overrides[get_user_service] = _get_user_service_override
    app.dependency_overrides[get_rate_limiter] = lambda: rate_limiter

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, email_service, rate_limiter

    app.dependency_overrides.clear()
    get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_register_endpoint_sends_code(api_client):
    client, email_service, rate_limiter = api_client

    response = await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "Passw0rd!1"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["detail"] == "Activation email sent"
    assert "alice@example.com" in email_service.sent_codes


@pytest.mark.asyncio
async def test_register_conflict_for_pending_user(api_client):
    client, *_ = api_client

    await client.post("/auth/register", json={"email": "bob@example.com", "password": "Passw0rd!1"})
    response = await client.post(
        "/auth/register", json={"email": "bob@example.com", "password": "Passw0rd!1"}
    )
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_register_conflict_for_active_user(api_client):
    client, email_service, _ = api_client

    await client.post("/auth/register", json={"email": "eve@example.com", "password": "Passw0rd!1"})
    code = email_service.sent_codes["eve@example.com"]
    await client.post(
        "/auth/activate",
        json={"code": code},
        auth=BasicAuth("eve@example.com", "Passw0rd!1"),
    )

    response = await client.post(
        "/auth/register", json={"email": "eve@example.com", "password": "Passw0rd!1"}
    )
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_register_invalid_payload_returns_422(api_client):
    client, *_ = api_client

    response = await client.post(
        "/auth/register", json={"email": "invalid-email", "password": "short"}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_activate_endpoint_success(api_client):
    client, email_service, rate_limiter = api_client

    await client.post(
        "/auth/register", json={"email": "carol@example.com", "password": "Passw0rd!1"}
    )
    code = email_service.sent_codes["carol@example.com"]

    response = await client.post(
        "/auth/activate",
        json={"code": code},
        auth=BasicAuth("carol@example.com", "Passw0rd!1"),
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["detail"] == "Account activated"

    invalid = await client.post(
        "/auth/activate",
        json={"code": code},
        auth=BasicAuth("carol@example.com", "Passw0rd!1"),
    )
    assert invalid.status_code == status.HTTP_400_BAD_REQUEST

    wrong_code = await client.post(
        "/auth/activate",
        json={"code": "9999"},
        auth=BasicAuth("carol@example.com", "Passw0rd!1"),
    )
    assert wrong_code.status_code == status.HTTP_400_BAD_REQUEST
    assert rate_limiter.activation_failures.get("carol@example.com") == 2


@pytest.mark.asyncio
async def test_activate_requires_basic_auth(api_client):
    client, email_service, _ = api_client

    await client.post(
        "/auth/register", json={"email": "unauth@example.com", "password": "Passw0rd!1"}
    )
    code = email_service.sent_codes["unauth@example.com"]

    response = await client.post("/auth/activate", json={"code": code})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    wrong = await client.post(
        "/auth/activate",
        json={"code": code},
        auth=BasicAuth("unauth@example.com", "wrong"),
    )
    assert wrong.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_resend_endpoint_requires_auth_and_sends_new_code(api_client):
    client, email_service, rate_limiter = api_client

    await client.post(
        "/auth/register", json={"email": "dave@example.com", "password": "Passw0rd!1"}
    )
    first_code = email_service.sent_codes["dave@example.com"]

    response = await client.post("/auth/resend", auth=BasicAuth("dave@example.com", "Passw0rd!1"))
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["detail"] == "Activation email resent"
    assert email_service.sent_codes["dave@example.com"] != first_code

    unauthorized = await client.post("/auth/resend", auth=BasicAuth("dave@example.com", "wrong"))
    assert unauthorized.status_code == status.HTTP_401_UNAUTHORIZED

    missing_auth = await client.post("/auth/resend")
    assert missing_auth.status_code == status.HTTP_401_UNAUTHORIZED
    assert rate_limiter.daily_resends.get("dave@example.com") == 1


@pytest.mark.asyncio
async def test_activate_rate_limited_after_failures(api_client):
    client, email_service, _ = api_client

    await client.post(
        "/auth/register", json={"email": "limit@example.com", "password": "Passw0rd!1"}
    )
    assert "limit@example.com" in email_service.sent_codes

    first = await client.post(
        "/auth/activate",
        json={"code": "0000"},
        auth=BasicAuth("limit@example.com", "Passw0rd!1"),
    )
    assert first.status_code == status.HTTP_400_BAD_REQUEST

    second = await client.post(
        "/auth/activate",
        json={"code": "0000"},
        auth=BasicAuth("limit@example.com", "Passw0rd!1"),
    )
    assert second.status_code == status.HTTP_400_BAD_REQUEST

    third = await client.post(
        "/auth/activate",
        json={"code": "0000"},
        auth=BasicAuth("limit@example.com", "Passw0rd!1"),
    )
    assert third.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_resend_rate_limited(api_client):
    client, email_service, rate_limiter = api_client

    await client.post(
        "/auth/register", json={"email": "spam@example.com", "password": "Passw0rd!1"}
    )
    assert email_service.sent_codes["spam@example.com"]

    first = await client.post(
        "/auth/resend",
        auth=BasicAuth("spam@example.com", "Passw0rd!1"),
    )
    assert first.status_code == status.HTTP_202_ACCEPTED

    second = await client.post(
        "/auth/resend",
        auth=BasicAuth("spam@example.com", "Passw0rd!1"),
    )
    assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_resend_active_user_conflict(api_client):
    client, email_service, rate_limiter = api_client

    await client.post("/auth/register", json={"email": "zoe@example.com", "password": "Passw0rd!1"})
    code = email_service.sent_codes["zoe@example.com"]
    await client.post(
        "/auth/activate",
        json={"code": code},
        auth=BasicAuth("zoe@example.com", "Passw0rd!1"),
    )

    response = await client.post("/auth/resend", auth=BasicAuth("zoe@example.com", "Passw0rd!1"))
    assert response.status_code == status.HTTP_409_CONFLICT
