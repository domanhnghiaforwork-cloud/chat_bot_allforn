import asyncio
from contextlib import asynccontextmanager, suppress
from uuid import UUID, uuid4

from app.config.settings import Settings
from app.rate_limit.redis_scripts import LOCK_REFRESH_LUA, LOCK_RELEASE_LUA
from app.redis_client import get_redis


class ConversationBusy(RuntimeError):
    pass


@asynccontextmanager
async def conversation_lock(conversation_id: UUID, settings: Settings):
    if not settings.redis_url and not settings.async_chat_enabled and not settings.queue_enabled:
        # Partial unique index PostgreSQL vẫn giữ single-flight trong chế độ rollback.
        yield
        return
    redis = get_redis()
    key = f"lock:conversation:{conversation_id}"
    owner = str(uuid4())
    ttl_ms = settings.worker_lease_seconds * 1000
    if not await redis.set(key, owner, nx=True, px=ttl_ms):
        raise ConversationBusy

    async def heartbeat() -> None:
        while True:
            await asyncio.sleep(settings.worker_lease_seconds / 3)
            if not await redis.eval(LOCK_REFRESH_LUA, 1, key, owner, ttl_ms):
                return

    task = asyncio.create_task(heartbeat())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await redis.eval(LOCK_RELEASE_LUA, 1, key, owner)
