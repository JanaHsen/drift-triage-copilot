# Worker process: dequeues action jobs from Redis and dispatches to handlers

import asyncio
import json
import signal
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker

import structlog

from app.core.config import settings
from app.db.base import build_engine
from app.db.models import ActionJob  # noqa: F401  — ensure model is loaded
from app.queue import build_redis_client
from app.workers.handlers import HANDLERS

logger = structlog.get_logger()

# Must match the keys used by the API's enqueue path.
_QUEUE_KEY = "platform:actions:queue"
_JOB_KEY_PREFIX = "platform:actions:job:"

_shutdown = False


def _handle_signal(signum, _frame):
    global _shutdown
    logger.info("Signal %d received; will exit after current job", signum)
    _shutdown = True


async def _process_job(redis_client, session_factory, job_id: str) -> None:
    job_key = f"{_JOB_KEY_PREFIX}{job_id}"
    raw = await redis_client.get(job_key)
    if raw is None:
        logger.error("Job payload missing in Redis for job_id=%s", job_id)
        return

    payload = json.loads(raw)
    action = payload["action"]
    handler = HANDLERS.get(action)
    if handler is None:
        logger.error("No handler registered for action=%s job_id=%s", action, job_id)
        return

    async with session_factory() as session:
        job = await session.get(ActionJob, UUID(job_id))
        if job is None:
            logger.error("ActionJob row not found in DB for job_id=%s", job_id)
            return

        job.status = "running"
        await session.commit()

        try:
            result = await handler(job, session)
            job.status = "succeeded"
            job.error_message = None
            job.completed_at = datetime.now(timezone.utc)
            # Append result to payload for audit visibility — keep original input intact.
            job.payload = {**(job.payload or {}), "result": result}
            await session.commit()
            logger.info("job=%s action=%s SUCCEEDED result=%s", job_id, action, result)
        except Exception as exc:
            logger.exception("job=%s action=%s FAILED", job_id, action)
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
        finally:
            # Clean up the queue payload regardless of outcome.
            await redis_client.delete(job_key)


async def main() -> None:
    redis_client = build_redis_client(settings.redis_url)
    engine = build_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    logger.info("Worker started. Polling %s", _QUEUE_KEY)
    try:
        while not _shutdown:
            # Block up to 5s for a job — keeps the loop responsive to shutdown.
            result = await redis_client.brpop([_QUEUE_KEY], timeout=5)
            if result is None:
                continue
            _, job_id = result
            logger.info("Dequeued job_id=%s", job_id)
            await _process_job(redis_client, session_factory, job_id)
    finally:
        logger.info("Worker shutting down")
        await redis_client.aclose()
        await engine.dispose()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    asyncio.run(main())
