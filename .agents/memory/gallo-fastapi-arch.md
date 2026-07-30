---
name: Gallo FastAPI architecture
description: Key decisions for the Gallo API backend (Python FastAPI + Supabase PostgREST proxy).
---

## Rule
FastAPI proxies all DB calls to Supabase PostgREST via httpx, forwarding the user's JWT in `Authorization: Bearer` headers. RLS is enforced server-side by Supabase exactly as it would be from the mobile client.

**Why:** SUPABASE_DB_URL provided was just a hostname (not a full postgresql:// DSN), making asyncpg unusable. PostgREST proxy is the canonical Supabase architecture anyway (as the endpoints doc specified: "Stack: Supabase PostgREST + RPC Postgres with RLS").

## How to apply
- `app/database.py` — `PostgREST` class wraps httpx; `db(jwt)` factory used in every route.
- All routers call `db(user["_token"]).select/insert/update/delete/rpc(...)`.
- Supabase RPCs called via `db(jwt).rpc("func_name", {...})` → `POST /rest/v1/rpc/func_name`.
- For multi-filter DELETEs (composite PK), use raw httpx directly (PostgREST needs `&col=eq.val` params, not the single-filter helper).
- `SUPABASE_DB_URL` secret is no longer needed. Required secrets: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`.
- Workflow run: `cd /home/runner/workspace/artifacts/api-server && uvicorn main:app --host 0.0.0.0 --port $PORT --reload`
