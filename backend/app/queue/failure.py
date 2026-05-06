from rq.job import Job

from app.queue.client import dlq


def handle_failure(job: Job, connection, type, value, traceback) -> None:
    dlq.enqueue(job.func_name, *job.args, **job.kwargs)
