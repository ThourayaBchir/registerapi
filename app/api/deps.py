"""Dependency providers for API routes."""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasicCredentials
from psycopg import AsyncConnection

from app.core.config import Settings, get_settings as load_settings
from app.core.database import get_db_conn
from app.core.security import (
    ensure_basic_credentials,
    get_basic_scheme,
    verify_password,
)
from app.repositories.activation import ActivationRepository
from app.repositories.user import UserRepository
from app.services.activation import ActivationService
from app.services.email import CeleryEmailService, EmailService
from app.services.user import UserService

_LOGGER = logging.getLogger(__name__)
_BASIC_SCHEME = get_basic_scheme()


async def get_settings() -> Settings:
    return load_settings()


async def get_db_connection() -> AsyncGenerator[AsyncConnection, None]:
    async with get_db_conn() as conn:
        yield conn


async def get_user_repository(
    connection: AsyncConnection = Depends(get_db_connection),
) -> UserRepository:
    return UserRepository(connection)


async def get_activation_repository(
    connection: AsyncConnection = Depends(get_db_connection),
) -> ActivationRepository:
    return ActivationRepository(connection)


def get_email_service() -> EmailService:
    return CeleryEmailService()


async def get_user_service(
    users: UserRepository = Depends(get_user_repository),
    codes: ActivationRepository = Depends(get_activation_repository),
    email_service: EmailService = Depends(get_email_service),
    settings: Settings = Depends(get_settings),
) -> UserService:
    return UserService(
        users=users,
        activation_codes=codes,
        email_service=email_service,
        settings=settings,
    )


async def get_activation_service(
    codes: ActivationRepository = Depends(get_activation_repository),
    users: UserRepository = Depends(get_user_repository),
) -> ActivationService:
    return ActivationService(codes=codes, users=users)


async def authenticate_basic_user(
    credentials: HTTPBasicCredentials | None,
    users: UserRepository,
) -> Dict[str, Any]:
    username, password = ensure_basic_credentials(credentials)

    user = await users.get_user_by_email(username)
    if user is None:
        _LOGGER.warning("Authentication failed: user not found", extra={"email": username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    if not verify_password(password, user["password_hash"]):
        _LOGGER.warning("Authentication failed: bad password", extra={"email": username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    sanitized = dict(user)
    sanitized.pop("password_hash", None)
    return sanitized


async def get_authenticated_user(
    credentials: HTTPBasicCredentials | None = Depends(_BASIC_SCHEME),
    users: UserRepository = Depends(get_user_repository),
) -> Dict[str, Any]:
    return await authenticate_basic_user(credentials, users)
