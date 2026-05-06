from rq import Worker

from app.queue.client import dlq, queue, redis_conn

if __name__ == "__main__":
    Worker([queue, dlq], connection=redis_conn).work()
