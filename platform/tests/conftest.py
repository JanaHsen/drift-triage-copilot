"""
Shared test setup. Runs before any test module is collected, so platform
modules can be imported safely.

Why we set env vars here: app.core.settings reads DATABASE_URL etc. at
module-import time via pydantic-settings. If a test imports anything that
transitively pulls in settings (auth, lifespan, routers), the import would
fail with a ValidationError when those vars aren't set. Conftest fires
before tests, so we satisfy the schema with throwaway values. Tests that
need real DB/Redis spin up containers separately.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("AGENT_TOKEN", "test-token")
os.environ.setdefault("AGENT_BASE_URL", "http://test-agent:8000")
