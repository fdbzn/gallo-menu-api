# Gallo API

App colaborativa para planear menús en equipo. Conecta encuestas grupales con listas de compras organizadas por lugar de compra.

## Flujo obligatorio al iniciar cualquier tarea

Sigue este orden. No saltes pasos salvo que la tarea sea trivial (typo, rename, etc.).

### 1. Graphify — barrido inicial al investigar el proyecto

Si vas a hacer un **barrido amplio** del repo (primera sesión, orientación general, arquitectura, "¿cómo funciona X?", explorar antes de implementar), **usa graphify primero** para mapear el codebase y **no leer a mano archivos que no aportan**.

#### Paso A — Usar el grafo existente (preferido)

Si existe `graphify-out/graph.json`:

1. Lee `graphify-out/GRAPH_REPORT.md` (god nodes, comunidades, conexiones)
2. Consulta con `graphify query "<pregunta>"` en lugar de abrir docenas de archivos
3. Solo abre en el editor los archivos que el grafo señale como relevantes

#### Paso B — Si no hay grafo o está desactualizado

Corre graphify sobre las carpetas útiles:

```bash
graphify update artifacts/api-server
```

#### Qué **omitir** del escaneo manual

| Path | Motivo |
|------|--------|
| `__pycache__/` | Bytecode compilado |
| `.venv/` | Entorno virtual |
| `graphify-out/` | Artefactos generados |
| `uv.lock` | Lockfile, no lógica |

#### Qué **sí** priorizar después del barrido

| Path | Motivo |
|------|--------|
| `artifacts/api-server/main.py` | App FastAPI y routers |
| `artifacts/api-server/app/` | Lógica de negocio |
| `AGENTS.md` | Este archivo |

### 2. Obsidian — contexto y planes aprobados

Si tienes conexión con el **MCP de Obsidian** (`obsidianprojects`), consulta el vault antes de tomar decisiones de arquitectura o producto:

| Nota | Ruta en vault |
|------|---------------|
| Decisiones y setup | `01-Projects/Gallo-table/` |
| Planes aprobados | `01-Projects/Gallo-table/Plans/` |

- Usa `search-vault` antes de escribir; nunca borres permanentemente.
- Si el usuario aprueba un plan, guárdalo en `01-Projects/Gallo-table/Plans/`.

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
- `artifacts/api-server/app/auth.py` — validación JWT: JWKS (ES256) + HS256 legacy
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
- `SUPABASE_JWT_SECRET` — secret HS256 legacy / tests (tokens reales ES256 usan JWKS)
- `SUPABASE_DB_URL` — connection string PostgreSQL directo

## User preferences

- Todo el backend en Python con FastAPI.
- Sin app móvil ni frontend — solo el servicio API.

## Tests

### Ejecutar

```bash
cd artifacts/api-server
uv run pytest tests/ -v          # 97 tests en 0.47s
uv run pytest tests/ -v -s       # con output del E2E
```

### Estructura

```
tests/
├── conftest.py          # Fixtures compartidos
├── test_perfiles.py     #  9 tests — Módulo 0
├── test_mesas.py        #  7 tests — Módulo 4
├── test_menus.py        # 13 tests — Módulo 5
├── test_amigos.py       #  5 tests — Módulo 6
├── test_platillos.py    # 14 tests — Módulo 7
├── test_ingredientes.py #  7 tests — Módulo 7g
├── test_listas.py       # 14 tests — Módulo 8
├── test_lugares.py      #  6 tests — Módulo 8
├── test_encuestas.py    # 17 tests — Módulo 9
└── test_e2e.py          #  1 test  — Flujo completo 2 usuarios
```

### Cómo funcionan

- **Unitarias**: mockean `PostgREST` → cada handler recibe datos simulados. Verifican status codes, respuestas y llamadas al mock.
- **E2E**: un solo test que ejecuta el journey real de Alice y Bob con una DB en memoria que persiste estado entre llamadas. Cubre crear mesa → menú → platillos → ingredientes → compartir → aceptar → encuesta → votar → cerrar → eliminar.

### Reglas de negocio cubiertas

| Regla | Descripción | Dónde se prueba |
|-------|-------------|-----------------|
| 6.2 | Relación de amistad mutua | E2E Fase 7 |
| 6.3 | Auto-amistad al compartir | E2E Fase 7 |
| 6.4 | Amigos primero en búsqueda | `test_perfiles.py` |
| 7.1.2 | Catálogo tipos de comida | `test_platillos.py` |
| 7.5.1-3 | CRUD ingredientes de platillo | `test_platillos.py` + E2E Fase 5 |
| 7.6 | Delete selectivo de platillo | `test_platillos.py` + E2E Fase 10 |
| 8.1 | Lista creada por trigger | E2E Fase 2 |
| 8.3 | Solo renombrar lista | `test_listas.py` |
| 8.5/8.7 | Mover a lugar / sin lugar | `test_listas.py` + E2E Fase 8 |
| 8.9 | Items sueltos sobreviven | `test_listas.py` |
| 8.11/8.12 | Asignar item a platillo | `test_listas.py` + E2E Fase 8 |
| 9.1-9.4 | CRUD encuestas, votar, cerrar | `test_encuestas.py` + E2E Fase 9 |
