from dataclasses import dataclass
from uuid import UUID

from app.config.settings import Settings
from app.rate_limit.redis_scripts import USER_BUCKET_LUA
from app.redis_client import get_redis


@dataclass(frozen=True, slots=True)
class UserLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


class UserLimiter:
    async def consume(self, user_id: UUID, settings: Settings) -> UserLimitResult:
        # Chế độ rollback v3 không bắt buộc Redis; khi đã cấu hình Redis thì lỗi
        # Redis vẫn fail-closed thay vì bỏ qua limiter.
        if not settings.redis_url and not settings.async_chat_enabled and not settings.queue_enabled:
            return UserLimitResult(True)
        result = await get_redis().eval(
            USER_BUCKET_LUA,
            1,
            f"rl:user:{user_id}:chat",
            settings.user_rate_capacity,
            settings.user_rate_refill_tokens,
            settings.user_rate_refill_seconds,
            1,
        )
        return UserLimitResult(bool(result[0]), max(1, (int(result[1]) + 999) // 1000))
