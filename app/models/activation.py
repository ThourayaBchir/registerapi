from pydantic import BaseModel, EmailStr


class ActivationRequest(BaseModel):
    email: EmailStr


class ActivationVerify(BaseModel):
    email: EmailStr
    code: str
