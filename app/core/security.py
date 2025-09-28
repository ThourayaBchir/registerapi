"""Security helpers for password hashing and basic authentication."""

from __future__ import annotations

import logging
from typing import Tuple

from fastapi import HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext

_LOGGER = logging.getLogger(__name__)
_PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
_HTTP_BASIC_SCHEME = HTTPBasic(auto_error=False)


def hash_password(raw_password: str) -> str:
    return _PWD_CONTEXT.hash(raw_password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    return _PWD_CONTEXT.verify(raw_password, hashed_password)


def get_basic_scheme() -> HTTPBasic:
    return _HTTP_BASIC_SCHEME


def ensure_basic_credentials(credentials: HTTPBasicCredentials | None) -> Tuple[str, str]:
    if credentials is None:
        _LOGGER.warning("Missing basic authentication credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username, credentials.password
