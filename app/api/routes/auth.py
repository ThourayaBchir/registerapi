from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_authenticated_user,
    get_user_service,
)
from app.models.activation import ActivationVerify
from app.models.user import UserCreate
from app.services.user import (
    UserAlreadyActiveError,
    UserPendingActivationError,
    UserService,
)

router = APIRouter()


@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
async def register_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    try:
        await service.register(payload.email, payload.password)
    except UserAlreadyActiveError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already active") from exc
    except UserPendingActivationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Activation code already issued") from exc

    return {"detail": "Activation email sent"}


@router.post("/resend", status_code=status.HTTP_202_ACCEPTED)
async def resend_activation_code(
    current_user: dict[str, Any] = Depends(get_authenticated_user),
    service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    email = current_user["email"]
    try:
        await service.request_activation_code(email)
    except UserAlreadyActiveError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already active") from exc

    return {"detail": "Activation email resent"}


@router.post("/activate", status_code=status.HTTP_200_OK)
async def activate_user(
    payload: ActivationVerify,
    service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    activated = await service.activate(payload.email, payload.code)
    if not activated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired activation code")

    return {"detail": "Account activated"}
