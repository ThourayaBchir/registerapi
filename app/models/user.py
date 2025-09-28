from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if value.strip() != value:
            raise ValueError("Password cannot contain leading or trailing spaces")
        return value


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
