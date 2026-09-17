from app.config.limits import CIRCUIT_FAILURE_THRESHOLD, CIRCUIT_OPEN_SECONDS
from app.config.settings import get_settings
from app.redis_client import get_redis


CIRCUIT_ALLOW_LUA = """
local status = redis.call('HGET', KEYS[1], 'status')
if not status or status == 'CLOSED' then return 1 end
local now = tonumber(redis.call('TIME')[1])
if status == 'OPEN' then
  local open_until = tonumber(redis.call('HGET', KEYS[1], 'open_until')) or 0
  if now < open_until then return 0 end
  if redis.call('SET', KEYS[2], '1', 'NX', 'EX', ARGV[1]) then
    redis.call('HSET', KEYS[1], 'status', 'HALF_OPEN')
    return 1
  end
end
return 0
"""

CIRCUIT_FAILURE_LUA = """
local failures = redis.call('INCR', KEYS[2])
redis.call('EXPIRE', KEYS[2], ARGV[2])
local status = redis.call('HGET', KEYS[1], 'status')
if failures >= tonumber(ARGV[1]) or status == 'HALF_OPEN' then
  local now = tonumber(redis.call('TIME')[1])
  redis.call('HMSET', KEYS[1], 'status', 'OPEN', 'open_until', now + tonumber(ARGV[2]))
  redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]) * 2)
  redis.call('DEL', KEYS[3])
end
return failures
"""


def _keys(project: str, model: str) -> tuple[str, str, str]:
    base = f"{project}:{model}"
    return f"circuit:{base}", f"circuit-fail:{base}", f"circuit-probe:{base}"


async def ensure_circuit_closed(project: str, model: str) -> bool:
    if not get_settings().redis_url:
        return True
    state, _, probe = _keys(project, model)
    return bool(
        await get_redis().eval(
            CIRCUIT_ALLOW_LUA, 2, state, probe, CIRCUIT_OPEN_SECONDS
        )
    )


async def record_success(project: str, model: str) -> None:
    if not get_settings().redis_url:
        return
    await get_redis().delete(*_keys(project, model))


async def record_failure(project: str, model: str) -> None:
    if not get_settings().redis_url:
        return
    state, failures, probe = _keys(project, model)
    await get_redis().eval(
        CIRCUIT_FAILURE_LUA,
        3,
        state,
        failures,
        probe,
        CIRCUIT_FAILURE_THRESHOLD,
        CIRCUIT_OPEN_SECONDS,
    )
