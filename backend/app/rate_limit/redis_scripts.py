USER_BUCKET_LUA = """
local now = redis.call('TIME')
local now_ms = now[1] * 1000 + math.floor(now[2] / 1000)
local capacity = tonumber(ARGV[1])
local refill_tokens = tonumber(ARGV[2])
local refill_ms = tonumber(ARGV[3]) * 1000
local cost = tonumber(ARGV[4])
local values = redis.call('HMGET', KEYS[1], 'tokens', 'updated_ms')
local tokens = tonumber(values[1]) or capacity
local updated = tonumber(values[2]) or now_ms
tokens = math.min(capacity, tokens + ((now_ms - updated) / refill_ms) * refill_tokens)
if tokens < cost then
  local retry_ms = math.ceil((cost - tokens) * refill_ms / refill_tokens)
  redis.call('HMSET', KEYS[1], 'tokens', tokens, 'updated_ms', now_ms)
  redis.call('PEXPIRE', KEYS[1], math.ceil(refill_ms * capacity / refill_tokens * 2))
  return {0, retry_ms}
end
tokens = tokens - cost
redis.call('HMSET', KEYS[1], 'tokens', tokens, 'updated_ms', now_ms)
redis.call('PEXPIRE', KEYS[1], math.ceil(refill_ms * capacity / refill_tokens * 2))
return {1, 0}
"""


MODEL_RESERVE_LUA = """
local now = redis.call('TIME')
local minute = math.floor(tonumber(now[1]) / 60)
local rpm_limit = tonumber(ARGV[1])
local tpm_limit = tonumber(ARGV[2])
local rpd_limit = tonumber(ARGV[3])
local tokens = tonumber(ARGV[4])
local rpm_window = tonumber(redis.call('HGET', KEYS[1], 'window'))
local tpm_window = tonumber(redis.call('HGET', KEYS[2], 'window'))
local rpm = rpm_window == minute and tonumber(redis.call('HGET', KEYS[1], 'count')) or 0
local tpm = tpm_window == minute and tonumber(redis.call('HGET', KEYS[2], 'count')) or 0
local rpd = tonumber(redis.call('GET', KEYS[3])) or 0
if rpm + 1 > rpm_limit or tpm + tokens > tpm_limit or rpd + 1 > rpd_limit then
  return {0, rpm, tpm, rpd, minute}
end
redis.call('HMSET', KEYS[1], 'window', minute, 'count', rpm + 1)
redis.call('HMSET', KEYS[2], 'window', minute, 'count', tpm + tokens)
redis.call('EXPIRE', KEYS[1], 120)
redis.call('EXPIRE', KEYS[2], 120)
redis.call('INCR', KEYS[3])
redis.call('EXPIRE', KEYS[3], tonumber(ARGV[5]))
return {1, rpm + 1, tpm + tokens, rpd + 1, minute}
"""


MODEL_RECONCILE_LUA = """
local window = tonumber(redis.call('HGET', KEYS[1], 'window'))
if window ~= tonumber(ARGV[1]) then return 0 end
local count = tonumber(redis.call('HGET', KEYS[1], 'count')) or 0
redis.call('HSET', KEYS[1], 'count', math.max(0, count + tonumber(ARGV[2])))
return 1
"""


LOCK_REFRESH_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('PEXPIRE', KEYS[1], ARGV[2])
end
return 0
"""


LOCK_RELEASE_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
return 0
"""
