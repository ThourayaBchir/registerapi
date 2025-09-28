from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


class ActivationRequest(BaseModel):
    email: EmailStr


class ActivationVerify(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{4}$", min_length=4, max_length=4)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("Activation code must contain only digits")
        return value
