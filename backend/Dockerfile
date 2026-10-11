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

# ---- runtime: production dependencies only, embedding model baked in, non-root -----------------
FROM base AS runtime
ENV HF_HOME=/opt/hf-cache \
    DATA_DIR=/data
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable
# Download the embedding model at build time so containers start fast and need no internet access.
ARG EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data/index \
    && chown -R app /opt/hf-cache /data
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=90s --retries=6 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "filings_qa.entrypoints.http.main:app", "--host", "0.0.0.0", "--port", "8000"]
