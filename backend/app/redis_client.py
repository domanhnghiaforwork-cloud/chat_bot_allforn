from functools import lru_cache

from redis.asyncio import Redis

from app.config.settings import get_settings


class RedisUnavailable(RuntimeError):
    pass


@lru_cache
def get_redis() -> Redis:
    settings = get_settings()
    if not settings.redis_url:
        raise RedisUnavailable("REDIS_URL chưa được cấu hình")
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=settings.redis_socket_timeout_seconds,
        socket_connect_timeout=settings.redis_socket_timeout_seconds,
    )


@lru_cache
def get_blocking_redis() -> Redis:
    """Client riêng cho XREAD BLOCK; không dùng timeout ngắn của limiter/lock."""
    settings = get_settings()
    if not settings.redis_url:
        raise RedisUnavailable("REDIS_URL chưa được cấu hình")
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=max(20.0, settings.redis_socket_timeout_seconds),
        socket_connect_timeout=settings.redis_socket_timeout_seconds,
    )


async def redis_ready() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False


async def close_redis_clients() -> None:
    for factory in (get_redis, get_blocking_redis):
        if factory.cache_info().currsize:
            await factory().aclose()
            factory.cache_clear()
