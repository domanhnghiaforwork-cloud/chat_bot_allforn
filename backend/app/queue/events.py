import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from app.redis_client import get_blocking_redis, get_redis


def event_key(request_id: UUID) -> str:
    return f"generation:events:{request_id}"


async def publish_event(
    request_id: UUID,
    event: str,
    data: dict[str, Any],
    ttl_seconds: int,
) -> str:
    redis = get_redis()
    key = event_key(request_id)
    event_id = await redis.xadd(
        key,
        {"event": event, "data": json.dumps(data, ensure_ascii=False)},
        maxlen=1000,
        approximate=True,
    )
    await redis.expire(key, ttl_seconds)
    return str(event_id)


async def stream_events(
    request_id: UUID, last_event_id: str = "0-0"
) -> AsyncIterator[str]:
    redis = get_blocking_redis()
    key = event_key(request_id)
    cursor = last_event_id
    while True:
        rows = await redis.xread({key: cursor}, count=100, block=15_000)
        if not rows:
            yield ": heartbeat\n\n"
            continue
        for _, events in rows:
            for event_id, fields in events:
                cursor = str(event_id)
                yield (
                    f"id: {cursor}\n"
                    f"event: {fields['event']}\n"
                    f"data: {fields['data']}\n\n"
                )
