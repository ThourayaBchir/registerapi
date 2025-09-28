from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.user import UserCreate


def test_user_create_password_strips_spaces() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="space@example.com", password=" secret ")


def test_user_create_password_min_length() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="short@example.com", password="short")


def test_user_create_valid_payload() -> None:
    payload = UserCreate(email="john@example.com", password="LongEnough1")
    assert payload.email == "john@example.com"
