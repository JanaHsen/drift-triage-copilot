FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# contracts is a sibling path-dependency declared in pyproject.toml as
# `path = "../contracts"`, which resolves to /contracts when WORKDIR is /app.
# Must be present before the first `uv sync`, since path deps are still
# resolved/installed even with --no-install-project.
COPY contracts /contracts

COPY backend/pyproject.toml backend/uv.lock backend/alembic.ini ./
RUN uv sync --frozen --no-install-project

COPY backend/app ./app
RUN uv sync --frozen

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]