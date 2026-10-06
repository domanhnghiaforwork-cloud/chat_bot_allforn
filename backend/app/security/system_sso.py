import secrets

import jwt
from fastapi import HTTPException
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.repository import users
from app.models import User
from app.redis_client import RedisUnavailable, get_redis
from app.security.password import hash_password_async


async def authenticate_system_ticket(session: AsyncSession, ticket: str) -> User:
    secret = get_settings().chatbot_sso_secret
    if len(secret) < 64:
        raise HTTPException(503, "Đăng nhập liên kết chưa được bật.")
    try:
        claims = jwt.decode(
            ticket, secret, algorithms=["HS256"],
            audience="olpai-chatbot", issuer="olpai-system",
            options={"require": ["exp", "iat", "sub", "email", "role", "jti", "type"]},
        )
        email = claims["email"]
        if (claims["type"] != "chatbot-sso" or claims["role"] not in ("admin", "user")
                or not isinstance(email, str) or "@" not in email or len(email) > 320
                or not isinstance(claims["jti"], str) or not 20 <= len(claims["jti"]) <= 100
                or claims["exp"] - claims["iat"] > 60):
            raise ValueError("Invalid ticket claims")
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, "Vé đăng nhập không hợp lệ hoặc đã hết hạn. Hãy mở lại từ system.") from None

    # Atomic across API workers; a captured ticket cannot create a second session.
    try:
        consumed = await get_redis().set(f"sso:used:{claims['jti']}", "1", nx=True, ex=90)
    except (RedisError, RedisUnavailable):
        raise HTTPException(503, "Dịch vụ đăng nhập liên kết tạm thời không sẵn sàng.") from None
    if not consumed:
        raise HTTPException(401, "Vé đăng nhập đã được sử dụng. Hãy mở lại từ system.")

    email = email.lower()
    user = await users.get_by_email(session, email)
    if user:
        # Existing chatbot permissions and password always remain authoritative.
        return user
    await session.commit()
    password_hash = await hash_password_async(secrets.token_urlsafe(48))
    user = User(email=email, password_hash=password_hash, role=claims["role"])
    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        await session.rollback()
        user = await users.get_by_email(session, email)
        if not user:
            raise
    return user
