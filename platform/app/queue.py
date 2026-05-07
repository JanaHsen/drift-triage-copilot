import json
from typing import Any

import structlog
import redis.asyncio as redis

logger = structlog.get_logger()

# Platform's Redis key prefix — keeps us out of backend's namespace.
_QUEUE_KEY = "platform:actions:queue"
_JOB_KEY_PREFIX = "platform:actions:job:"
_IDEMPOTENCY_KEY_PREFIX = "platform:actions:idempotency:"

# Idempotency entries live for 24h — long enough to dedupe retries, short
# enough to not pile up forever.
_IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60


def build_redis_client(redis_url: str) -> redis.Redis:
    """Async Redis client. Decoded responses so we work with str, not bytes."""
    return redis.from_url(redis_url, decode_responses=True)


async def claim_idempotency_key(
    client: redis.Redis, idempotency_key: str, job_id: str
) -> str | None:
    """
    Atomic check-and-set. Returns existing job_id if key already claimed,
    else None (meaning this is the first time we've seen this key).

    Uses SET NX so two concurrent calls can't both think they're first.
    """
    key = f"{_IDEMPOTENCY_KEY_PREFIX}{idempotency_key}"
    was_set = await client.set(key, job_id, nx=True, ex=_IDEMPOTENCY_TTL_SECONDS)
    if was_set:
        return None
    return await client.get(key)


async def enqueue_job(
    client: redis.Redis, job_id: str, payload: dict[str, Any]
) -> None:
    """Push a job onto the queue and store its full payload for the worker."""
    job_key = f"{_JOB_KEY_PREFIX}{job_id}"
    await client.set(job_key, json.dumps(payload))
    await client.lpush(_QUEUE_KEY, job_id)
    logger.info("queue.enqueued", job_id=job_id, action=payload.get("action"))
