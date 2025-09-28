from __future__ import annotations

import string

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if value.strip() != value:
            raise ValueError("Password cannot contain leading or trailing spaces")

        if any(ch.isspace() for ch in value):
            raise ValueError("Password cannot contain whitespace characters")

        has_lower = any(ch.islower() for ch in value)
        has_upper = any(ch.isupper() for ch in value)
        has_digit = any(ch.isdigit() for ch in value)
        has_special = any(ch in string.punctuation for ch in value)

        if not (has_lower and has_upper and has_digit and has_special):
            raise ValueError(
                "Password must include at least one lowercase letter, one uppercase "
                "letter, one digit, and one special character"
            )
        return value


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
