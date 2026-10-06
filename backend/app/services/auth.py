from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import users
from app.models import User
from app.security.password import hash_password_async, verify_password_async


class EmailAlreadyExistsError(Exception):
    pass


async def register(session: AsyncSession, email: str, password: str) -> User:
    if await users.get_by_email(session, email):
        raise EmailAlreadyExistsError
    try:
        await session.commit()
        password_hash = await hash_password_async(password)
        user = await users.create(session, email, password_hash)
        await session.commit()
        await session.refresh(user)
        return user
    except IntegrityError as exc:
        await session.rollback()
        raise EmailAlreadyExistsError from exc


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    user = await users.get_by_email(session, email)
    if not user:
        return None
    await session.commit()
    if not await verify_password_async(password, user.password_hash):
        return None
    return user
