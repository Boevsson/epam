# syntax=docker/dockerfile:1

# ---- base: Python 3.12 + uv, shared by every stage --------------------------------------------
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# ---- dev: every dependency group plus the test suite -------------------------------------------
# `docker compose run --rm --build tests` runs the same quality gate as `make check`.
FROM base AS dev
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen
CMD ["sh", "scripts/check.sh"]
