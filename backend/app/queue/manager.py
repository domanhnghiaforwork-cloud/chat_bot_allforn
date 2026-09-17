import time
from dataclasses import dataclass
from uuid import UUID

from app.redis_client import get_redis


JOBS_STREAM = "generation:jobs"
DELAYED_SET = "generation:delayed"
WORKER_GROUP = "gemini-workers"
ACTIVE_SET = "generation:active-queue"

ENQUEUE_LUA = """
local size = redis.call('SCARD', KEYS[2])
if redis.call('SISMEMBER', KEYS[2], ARGV[1]) == 1 then return {1, size} end
if size >= tonumber(ARGV[2]) then return {0, size} end
redis.call('SADD', KEYS[2], ARGV[1])
redis.call('XADD', KEYS[1], 'MAXLEN', '~', ARGV[3], '*', 'request_id', ARGV[1])
return {1, size + 1}
"""

RECOVER_LUA = """
local size = redis.call('SCARD', KEYS[2])
local exists = redis.call('SISMEMBER', KEYS[2], ARGV[1])
if exists == 0 and size >= tonumber(ARGV[2]) then return 0 end
redis.call('SADD', KEYS[2], ARGV[1])
redis.call('XADD', KEYS[1], 'MAXLEN', '~', ARGV[3], '*', 'request_id', ARGV[1])
return 1
"""

PROMOTE_LUA = """
local due = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, ARGV[2])
local moved = 0
for _, request_id in ipairs(due) do
  if redis.call('ZREM', KEYS[1], request_id) == 1 then
    redis.call('XADD', KEYS[2], 'MAXLEN', '~', ARGV[3], '*', 'request_id', request_id)
    moved = moved + 1
  end
end
return moved
"""


class QueueFull(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EnqueueResult:
    position: int


class QueueManager:
    async def ensure_group(self) -> None:
        try:
            await get_redis().xgroup_create(JOBS_STREAM, WORKER_GROUP, id="0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def enqueue(self, request_id: UUID, max_size: int) -> EnqueueResult:
        result = await get_redis().eval(
            ENQUEUE_LUA, 2, JOBS_STREAM, ACTIVE_SET, str(request_id), max_size, max_size * 2
        )
        if not result[0]:
            raise QueueFull
        return EnqueueResult(int(result[1]))

    async def delay(self, request_id: UUID, delay_seconds: float) -> None:
        await get_redis().zadd(
            DELAYED_SET, {str(request_id): time.time() + max(0, delay_seconds)}
        )

    async def recover(self, request_id: UUID, max_size: int) -> None:
        # Recovery phải tạo stream entry mới kể cả active-set còn dữ liệu cũ.
        accepted = await get_redis().eval(
            RECOVER_LUA,
            2,
            JOBS_STREAM,
            ACTIVE_SET,
            str(request_id),
            max_size,
            max_size * 2,
        )
        if not accepted:
            raise QueueFull

    async def promote_due(self, max_size: int, batch_size: int = 100) -> int:
        return int(
            await get_redis().eval(
                PROMOTE_LUA,
                2,
                DELAYED_SET,
                JOBS_STREAM,
                time.time(),
                batch_size,
                max_size * 2,
            )
        )

    async def ack(self, message_id: str) -> None:
        # Xóa entry đã ACK để stream không tích lịch sử rồi trim nhầm pending job.
        pipeline = get_redis().pipeline(transaction=True)
        pipeline.xack(JOBS_STREAM, WORKER_GROUP, message_id)
        pipeline.xdel(JOBS_STREAM, message_id)
        await pipeline.execute()

    async def complete(self, request_id: UUID) -> None:
        await get_redis().srem(ACTIVE_SET, str(request_id))

    async def depth(self) -> int:
        return int(await get_redis().scard(ACTIVE_SET))
