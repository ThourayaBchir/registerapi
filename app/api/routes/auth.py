from fastapi import APIRouter

router = APIRouter()


@router.post("/register")
async def register_user() -> dict[str, str]:
    return {"detail": "placeholder"}


@router.post("/activate")
async def activate_user() -> dict[str, str]:
    return {"detail": "placeholder"}
