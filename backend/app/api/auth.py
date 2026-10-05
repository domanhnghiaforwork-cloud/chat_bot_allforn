from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

from app.db.database import get_session
from app.schemas.auth import AuthCredentials, LoginCredentials, TokenResponse
from app.security.jwt import create_access_token
from app.services import auth as service
from app.security.system_sso import authenticate_system_ticket
from app.security.system_provisioning import provision_system_account

router = APIRouter(prefix="/auth", tags=["auth"])


class SystemTicket(BaseModel):
    ticket: str = Field(min_length=1, max_length=4096)


@router.post("/system-provision")
async def system_provision(payload: SystemTicket, session: AsyncSession = Depends(get_session)):
    created = await provision_system_account(session, payload.ticket)
    return JSONResponse({"created": created}, headers={"Cache-Control": "no-store"})


@router.post("/system-sso", response_model=TokenResponse)
async def system_sso(payload: SystemTicket, session: AsyncSession = Depends(get_session)):
    user = await authenticate_system_ticket(session, payload.ticket)
    response = TokenResponse(access_token=create_access_token(user.id), user=user)
    return JSONResponse(response.model_dump(mode="json"), headers={"Cache-Control": "no-store"})


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
    payload: LoginCredentials,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user = await service.authenticate(session, str(payload.email), payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng",
        )
    return TokenResponse(access_token=create_access_token(user.id), user=user)
