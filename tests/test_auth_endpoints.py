from __future__ import annotations

import os

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, BasicAuth

from app.api.deps import get_db_connection, get_user_service
from app.core.config import get_settings
from app.main import app
from app.repositories.activation import ActivationRepository
from app.repositories.user import UserRepository
from app.services.email import EmailService
from app.services.user import UserService


class StubEmailService(EmailService):
    def __init__(self) -> None:
        self.sent_codes: dict[str, str] = {}

    async def send_activation(self, email: str, code: str, ttl_seconds: int) -> None:
        self.sent_codes[email] = code


@pytest_asyncio.fixture
async def api_client(db_conn, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", os.getenv("TEST_DATABASE_URL", "postgresql://register:register@postgres:5432/user_activation"))
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("EMAIL_API_URL", "https://email-api.example.com/v1/send")
    monkeypatch.setenv("SYSTEM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("SECRET_KEY", "secret")

    get_settings.cache_clear()  # type: ignore[attr-defined]

    email_service = StubEmailService()
    user_repo = UserRepository(db_conn)
    activation_repo = ActivationRepository(db_conn)
    settings = get_settings()
    service = UserService(user_repo, activation_repo, email_service, settings)

    async def _get_db_connection_override():
        yield db_conn

    async def _get_user_service_override():
        return service

    app.dependency_overrides[get_db_connection] = _get_db_connection_override
    app.dependency_overrides[get_user_service] = _get_user_service_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, email_service

    app.dependency_overrides.clear()
    get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_register_endpoint_sends_code(api_client):
    client, email_service = api_client

    response = await client.post("/auth/register", json={"email": "alice@example.com", "password": "Passw0rd!1"})
    assert response.status_code == 202
    assert response.json()["detail"] == "Activation email sent"
    assert "alice@example.com" in email_service.sent_codes


@pytest.mark.asyncio
async def test_register_conflict_for_pending_user(api_client):
    client, _ = api_client

    await client.post("/auth/register", json={"email": "bob@example.com", "password": "Passw0rd!1"})
    response = await client.post("/auth/register", json={"email": "bob@example.com", "password": "Passw0rd!1"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_activate_endpoint_success(api_client):
    client, email_service = api_client

    await client.post("/auth/register", json={"email": "carol@example.com", "password": "Passw0rd!1"})
    code = email_service.sent_codes["carol@example.com"]

    response = await client.post("/auth/activate", json={"email": "carol@example.com", "code": code})
    assert response.status_code == 200
    assert response.json()["detail"] == "Account activated"

    invalid = await client.post("/auth/activate", json={"email": "carol@example.com", "code": code})
    assert invalid.status_code == 400


@pytest.mark.asyncio
async def test_resend_endpoint_requires_auth_and_sends_new_code(api_client):
    client, email_service = api_client

    await client.post("/auth/register", json={"email": "dave@example.com", "password": "Passw0rd!1"})
    first_code = email_service.sent_codes["dave@example.com"]

    response = await client.post("/auth/resend", auth=BasicAuth("dave@example.com", "Passw0rd!1"))
    assert response.status_code == 202
    assert response.json()["detail"] == "Activation email resent"
    assert email_service.sent_codes["dave@example.com"] != first_code

    unauthorized = await client.post("/auth/resend", auth=BasicAuth("dave@example.com", "wrong"))
    assert unauthorized.status_code == 401
