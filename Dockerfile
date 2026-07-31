# ── Stage 1: uv binary ────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.7.14 AS uv

# ── Stage 2: runtime ───────────────────────────────────────────────────────────
FROM python:3.11-slim

# System deps (none needed for pure Python, but kept for future native deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary
COPY --from=uv /uv /usr/local/bin/uv

# Optimizations for container builds
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# ── Dependencies layer (cache-friendly) ────────────────────────────────────────
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ── Source code ────────────────────────────────────────────────────────────────
COPY artifacts/ artifacts/

# ── Runtime ────────────────────────────────────────────────────────────────────
WORKDIR /app/artifacts/api-server

# Cloud Run provides $PORT, default to 8080 for local testing
EXPOSE 8080

CMD ["sh", "-c", "exec uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --no-access-log"]
