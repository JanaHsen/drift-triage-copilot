import redis
from rq import Queue

from app.core.config import settings

redis_conn = redis.from_url(settings.redis_url)
queue = Queue("drift-triage", connection=redis_conn)
dlq = Queue("drift-triage-dlq", connection=redis_conn)
