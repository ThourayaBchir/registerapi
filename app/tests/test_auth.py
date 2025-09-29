from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from app.api.deps import authenticate_basic_user
from app.core.security import hash_password
from app.repositories.user import UserRepository


@pytest.mark.asyncio
async def test_basic_auth_success(db_conn) -> None:
    repo = UserRepository(db_conn)
    await repo.create_user("alice@example.com", hash_password("SuperSecret1!"))

    credentials = HTTPBasicCredentials(username="alice@example.com", password="SuperSecret1!")
    user = await authenticate_basic_user(credentials, repo)

    assert user["email"] == "alice@example.com"
    assert "password_hash" not in user


@pytest.mark.asyncio
async def test_basic_auth_wrong_password(db_conn) -> None:
    repo = UserRepository(db_conn)
    await repo.create_user("bob@example.com", hash_password("CorrectHorse1!"))

    credentials = HTTPBasicCredentials(username="bob@example.com", password="WrongPassword")
    with pytest.raises(HTTPException) as exc:
        await authenticate_basic_user(credentials, repo)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_basic_auth_unknown_user(db_conn) -> None:
    repo = UserRepository(db_conn)
    credentials = HTTPBasicCredentials(username="ghost@example.com", password="whatever")

    with pytest.raises(HTTPException) as exc:
        await authenticate_basic_user(credentials, repo)

    assert exc.value.status_code == 401
