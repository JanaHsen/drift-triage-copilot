import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("AGENT_TOKEN", "test-token")
os.environ.setdefault("AGENT_BASE_URL", "http://test-agent:8000")
