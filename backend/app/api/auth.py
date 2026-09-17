from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.schemas.auth import AuthCredentials, TokenResponse
from app.security.jwt import create_access_token
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: AuthCredentials,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    try:
        user = await service.register(session, str(payload.email), payload.password)
        return TokenResponse(access_token=create_access_token(user.id), user=user)
    except service.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email đã được sử dụng",
        ) from None


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: AuthCredentials,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user = await service.authenticate(session, str(payload.email), payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng",
        )
    return TokenResponse(access_token=create_access_token(user.id), user=user)
