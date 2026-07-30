# Gallo API

App colaborativa para planear menús en equipo. Conecta encuestas grupales con listas de compras organizadas por lugar de compra.

## Run & Operate

- `cd artifacts/api-server && uvicorn main:app --host 0.0.0.0 --port 8080 --reload` — correr el servidor en desarrollo
- Docs interactivas: `http://localhost:8080/api/docs`
- Health check: `GET /api/healthz`

## Stack

- Python 3.11 + FastAPI + Uvicorn
- asyncpg — driver PostgreSQL async (conexión directa a Supabase)
- python-jose — validación JWT de Supabase Auth
- pydantic-settings — configuración desde env vars
- Supabase PostgreSQL con RLS nativo

## Where things live

- `artifacts/api-server/main.py` — app FastAPI y lifespan (pool init/close)
- `artifacts/api-server/app/database.py` — pool asyncpg + contexto RLS por request
- `artifacts/api-server/app/auth.py` — validación JWT con SUPABASE_JWT_SECRET
- `artifacts/api-server/app/deps.py` — dependencia `get_current_user`
- `artifacts/api-server/app/routers/` — 9 routers por módulo de negocio

## Architecture decisions

- **RLS enforced vía set_config**: cada request abre una transacción y ejecuta `set_config('role','authenticated',true)` + `set_config('request.jwt.claims', ..., true)` para que las políticas RLS de Supabase funcionen igual que con PostgREST.
- **No ORM**: queries SQL directas con asyncpg; el esquema vive en Supabase, no en el código.
- **Triggers DB no duplicados**: create lista, sync items, auto-amistad viven en Postgres triggers; los endpoints no reimplementan esa lógica.
- **JWT solo Auth del cliente**: signUp/signIn/signOut los maneja el SDK de Supabase en el cliente; el backend solo valida el JWT resultante.

## Módulos implementados

| # | Módulo | Endpoints |
|---|--------|-----------|
| 0 | Perfiles y búsqueda | GET /perfiles/me, PATCH /perfiles/me, GET /perfiles/buscar |
| 4 | Mesas de trabajo | CRUD /mesas_trabajo |
| 5 | Menús y compartición | CRUD /menus, /menu_platillos, /menu_compartido |
| 6 | Amigos | GET/POST /amigos, /amigos/agregar |
| 7 | Platillos e ingredientes | CRUD /platillos, /platillo_ingredientes, /cat_tipos_comida |
| 7g | Ingredientes globales | CRUD /ingredientes |
| 8 | Listas de compras | GET/PATCH /listas_compras, /lista_compra_items, RPCs assign |
| 8 | Lugares de compra | CRUD /lugares_compra |
| 9 | Encuestas | CRUD /encuestas, /encuesta_opciones, /encuesta_votos, RPC votar |

## Required secrets

- `SUPABASE_URL` — URL del proyecto Supabase
- `SUPABASE_ANON_KEY` — clave anon/public
- `SUPABASE_JWT_SECRET` — JWT secret para validar tokens
- `SUPABASE_DB_URL` — connection string PostgreSQL directo

## User preferences

- Todo el backend en Python con FastAPI.
- Sin app móvil ni frontend — solo el servicio API.
