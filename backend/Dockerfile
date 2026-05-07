FROM python:3.12-slim

# Pull just the uv binary out of the official image — fast, cacheable, no apt deps.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Reverted from the unified-pyproject change — Rasha's per-service file is the
# complete one for the backend's runtime needs. Discuss the unification with
# her before re-applying. The platform/Dockerfile correctly uses the root
# pyproject because all of the platform's deps live there.
COPY backend/pyproject.toml backend/uv.lock backend/alembic.ini ./
RUN uv sync --frozen --no-install-project

# Copy source, then install the project package itself.
COPY backend/app ./app
COPY contracts ./contracts
RUN uv sync --frozen

# Default command — overridden per service in docker-compose.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]