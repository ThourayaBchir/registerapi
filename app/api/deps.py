"""Dependency providers for API routes."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from psycopg import AsyncConnection

from app.core.config import Settings, get_settings as load_settings
from app.core.database import get_db_conn
from app.repositories.activation import ActivationRepository
from app.repositories.user import UserRepository
from app.services.activation import ActivationService
from app.services.email import CeleryEmailService, EmailService
from app.services.user import UserService


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
    email_service: EmailService = Depends(get_email_service),
) -> UserService:
    return UserService(users=users, email_service=email_service)


async def get_activation_service(
    codes: ActivationRepository = Depends(get_activation_repository),
) -> ActivationService:
    return ActivationService(codes=codes)
