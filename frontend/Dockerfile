FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY frontend/pyproject.toml frontend/uv.lock ./
RUN uv sync --frozen --no-install-project

COPY frontend/app.py ./

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
