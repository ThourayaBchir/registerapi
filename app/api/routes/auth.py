from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_authenticated_user,
    get_rate_limiter,
    get_user_service,
)
from app.models.activation import ActivationVerify
from app.models.user import UserCreate
from app.services.user import (
    UserAlreadyActiveError,
    UserPendingActivationError,
    UserService,
)
from app.services.rate_limiter import RateLimitExceeded, RateLimiter

router = APIRouter()


def _retry_after_headers(exc: RateLimitExceeded) -> dict[str, str]:
    if exc.retry_after is None or exc.retry_after < 0:
        return {}
    return {"Retry-After": str(exc.retry_after)}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> dict[str, str]:
    try:
        await service.register(payload.email, payload.password)
    except UserAlreadyActiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already active"
        ) from exc
    except UserPendingActivationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Activation code already issued"
        ) from exc

    return {"detail": "Activation email sent"}


@router.post("/resend", status_code=status.HTTP_202_ACCEPTED)
async def resend_activation_code(
    current_user: Annotated[dict[str, Any], Depends(get_authenticated_user)],
    service: Annotated[UserService, Depends(get_user_service)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> dict[str, str]:
    email = current_user["email"]
    try:
        await limiter.ensure_resend_allowed(email)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers=_retry_after_headers(exc),
        ) from exc
    try:
        await service.request_activation_code(email)
    except UserAlreadyActiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already active"
        ) from exc

    await limiter.record_resend(email)

    return {"detail": "Activation email resent"}


@router.post("/activate", status_code=status.HTTP_200_OK)
async def activate_user(
    payload: ActivationVerify,
    current_user: Annotated[dict[str, Any], Depends(get_authenticated_user)],
    service: Annotated[UserService, Depends(get_user_service)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> dict[str, str]:
    email = current_user["email"]
    try:
        await limiter.ensure_activation_allowed(email)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers=_retry_after_headers(exc),
        ) from exc
    activated = await service.activate(email, payload.code)
    if not activated:
        await limiter.record_activation_failure(email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired activation code"
        )

    await limiter.reset_activation(email)

    return {"detail": "Account activated"}
