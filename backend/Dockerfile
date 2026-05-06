FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first — layer is cached until pyproject.toml or uv.lock changes
COPY backend/pyproject.toml backend/uv.lock backend/alembic.ini ./
RUN uv sync --frozen --no-install-project

# Copy source, then install the project package itself
COPY backend/app ./app
COPY contracts ./contracts
RUN uv sync --frozen

# Default command — overridden per service in docker-compose
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
