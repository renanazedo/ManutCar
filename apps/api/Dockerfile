# STAGE 1: Builder
FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Preservar a estrutura do monorepo usada pelas dependências locais em apps/api/pyproject.toml
COPY packages/db ./packages/db
COPY packages/schemas ./packages/schemas
COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md ./apps/api/

WORKDIR /app/apps/api

RUN uv sync --frozen --no-dev --no-install-project

# Copiar o código da API após resolver o lockfile
COPY apps/api/app ./app

# Instalar o pacote local da API
RUN uv pip install --no-deps .

# STAGE 2: Runtime
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    PATH="/app/apps/api/.venv/bin:$PATH"

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

COPY --from=builder --chown=appuser:appuser /app/apps/api/.venv /app/apps/api/.venv
COPY --from=builder --chown=appuser:appuser /app/apps/api/app /app/apps/api/app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=5)" || exit 1

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000", "app.main:app"]