"""Create-only provisioning; never issues a session or replaces an account."""
import jwt
from argon2 import extract_parameters, Type
from fastapi import HTTPException
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.repository import users
from app.models import User


async def provision_system_account(session: AsyncSession, ticket: str) -> bool:
    settings = get_settings()
    if not settings.chatbot_account_sync_enabled or len(settings.chatbot_sso_secret) < 64:
        raise HTTPException(503, "Đồng bộ tài khoản chưa được bật.")
    try:
        claims = jwt.decode(
            ticket, settings.chatbot_sso_secret, algorithms=["HS256"],
            audience="olpai-chatbot", issuer="olpai-system",
            options={"require": ["exp", "iat", "sub", "email", "role", "jti", "type", "password_hash"]},
        )
        if (claims["type"] != "chatbot-provision" or claims["role"] not in ("admin", "user")
                or not isinstance(claims["jti"], str) or not 20 <= len(claims["jti"]) <= 100
                or not 0 < claims["exp"] - claims["iat"] <= 60):
            raise ValueError("Invalid provisioning claims")
        email = str(TypeAdapter(EmailStr).validate_python(claims["email"])).lower()
        password_hash = claims["password_hash"]
        if not isinstance(password_hash, str) or len(password_hash) > 255:
            raise ValueError("Invalid password hash")
        params = extract_parameters(password_hash)
        if (params.type != Type.ID or params.version != 19
                or not 8192 <= params.memory_cost <= 262144
                or not 1 <= params.time_cost <= 10 or not 1 <= params.parallelism <= 16
                or params.salt_len < 16 or params.hash_len < 32):
            raise ValueError("Unsupported password hash")
    except (jwt.PyJWTError, ValueError, TypeError, ValidationError):
        raise HTTPException(401, "Yêu cầu đồng bộ tài khoản không hợp lệ hoặc đã hết hạn.") from None

    if await users.get_by_email(session, email):
        return False
    user = User(email=email, password_hash=password_hash, role=claims["role"])
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        if not await users.get_by_email(session, email):
            raise
        return False
    return True
