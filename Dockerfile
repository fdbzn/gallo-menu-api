# ── Etapa 1: Builder — instalar dependencias ──────────────────────────────────
FROM python:3.11-slim AS builder

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Etapa 2: Final — imagen ligera ─────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Usuario no-root
RUN addgroup --system nonroot && adduser --system --group nonroot

# Copiar dependencias instaladas desde builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código fuente
COPY artifacts/ artifacts/

RUN chown -R nonroot:nonroot /app
USER nonroot

WORKDIR /app/artifacts/api-server

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --no-access-log"]
