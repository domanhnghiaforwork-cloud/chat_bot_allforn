from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError
import asyncio
from starlette.concurrency import run_in_threadpool

password_hash = PasswordHash.recommended()
_password_slots = asyncio.Semaphore(2)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(password, hashed_password)
    except PwdlibError:
        return False


async def hash_password_async(password: str) -> str:
    # Argon2 uses substantial RAM per hash. Bound both CPU and memory during
    # simultaneous logins/registrations without blocking the event loop.
    async with _password_slots:
        return await run_in_threadpool(hash_password, password)


async def verify_password_async(password: str, hashed_password: str) -> bool:
    async with _password_slots:
        return await run_in_threadpool(verify_password, password, hashed_password)
