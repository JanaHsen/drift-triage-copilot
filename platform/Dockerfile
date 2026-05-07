# Multi-stage uv install: pull just the binary out of the official image.
# Cleaner than the curl-shell install, smaller final image, no apt dependencies.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Two-step layer-cache strategy: install third-party deps first (slow, rarely
# changes), then install the project itself (fast, changes every commit).
# Without this split, a one-line code change reinstalls every package.
COPY platform/pyproject.toml platform/uv.lock ./
RUN uv sync --frozen --no-install-project

# Now the application code. This layer rebuilds on every code change but the
# heavy dependency layer above stays cached.
COPY platform/app ./app
COPY contracts ./contracts
RUN uv sync --frozen

# Run as non-root. Container security 101.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
