from __future__ import annotations

import pytest

from app.repositories.activation import ActivationRepository
from app.repositories.user import UserRepository
from app.utils.code_generator import generate_code


@pytest.mark.asyncio
async def test_create_and_fetch_user(db_conn) -> None:
    repo = UserRepository(db_conn)

    user_id = await repo.create_user("jane@example.com", "hashed-password")
    user = await repo.get_user_by_email("jane@example.com")

    assert user is not None
    assert user["id"] == user_id
    assert user["is_active"] is False


@pytest.mark.asyncio
async def test_create_and_validate_activation_code(db_conn) -> None:
    user_repo = UserRepository(db_conn)
    activation_repo = ActivationRepository(db_conn)

    await user_repo.create_user("john@example.com", "hashed")

    code = generate_code()
    await activation_repo.create_code("john@example.com", code, ttl_seconds=60)

    assert await activation_repo.validate_code("john@example.com", code) is True
    # Second validation should fail because code has been marked as used.
    assert await activation_repo.validate_code("john@example.com", code) is False


@pytest.mark.asyncio
async def test_activation_code_expires(db_conn) -> None:
    activation_repo = ActivationRepository(db_conn)

    await activation_repo.create_code("expired@example.com", "0001", ttl_seconds=0)

    assert await activation_repo.validate_code("expired@example.com", "0001") is False
