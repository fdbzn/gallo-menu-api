# Gallo Menu API

Backend API colaborativo para planear menús en equipo, gestionar encuestas grupales y organizar listas de compras por lugar de compra.

## 🚀 Tech Stack

- **Framework:** FastAPI (Python 3.11+) + Uvicorn
- **Base de datos:** PostgreSQL / Supabase con RLS nativo
- **Driver DB:** asyncpg (conexiones directas y pooled)
- **Autenticación:** Supabase Auth (JWT ES256 / JWKS)

## ⚙️ Configuración rápida

1. **Variables de entorno:**
   ```bash
   cp .env.example .env
   # Configura SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_DB_URL, etc.
   ```

2. **Instalar dependencias:**
   ```bash
   uv sync
   ```

3. **Ejecutar en desarrollo:**
   ```bash
   cd artifacts/api-server
   uvicorn main:app --host 0.0.0.0 --port 8080 --reload
   ```
   - **Documentación Swagger:** `http://localhost:8080/api/docs`
   - **Health check:** `http://localhost:8080/api/healthz`

## 🧪 Pruebas

```bash
cd artifacts/api-server
uv run pytest tests/ -v
```
