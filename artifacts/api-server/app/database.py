"""Supabase PostgREST client using httpx.

Each request supplies a user JWT which is forwarded to PostgREST so that
Supabase Row-Level Security policies are applied exactly as they would be
from the mobile client.
"""
from contextlib import asynccontextmanager
import httpx
from typing import Any, Optional

from app.config import settings


class PostgRESTError(Exception):
    def __init__(self, status_code: int, detail: Any) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


class PostgREST:
    """Thin async wrapper around Supabase PostgREST + RPC endpoints."""

    def __init__(self, jwt: str) -> None:
        self._base = f"{settings.supabase_url}/rest/v1"
        self._headers = {
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json",
        }

    # ── low-level helpers ────────────────────────────────────────────────────

    async def _req(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json: Optional[Any] = None,
        prefer: str = "return=representation",
    ) -> Any:
        headers = {**self._headers, "Prefer": prefer}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.request(
                method,
                f"{self._base}{path}",
                headers=headers,
                params=params,
                json=json,
            )
        if resp.status_code == 404 or resp.status_code == 406:
            return None
        if not resp.is_success:
            detail: Any = resp.text
            if resp.content:
                try:
                    detail = resp.json()
                except Exception:
                    pass
            raise PostgRESTError(resp.status_code, detail)
        if resp.content:
            return resp.json()
        return None

    # ── public API ───────────────────────────────────────────────────────────

    async def select(self, table: str, params: dict | None = None) -> list:
        result = await self._req("GET", f"/{table}", params=params, prefer="")
        return result or []

    async def select_one(self, table: str, params: dict | None = None) -> dict | None:
        p = dict(params or {})
        p["limit"] = "1"
        rows = await self.select(table, p)
        return rows[0] if rows else None

    async def insert(self, table: str, data: dict) -> dict:
        try:
            result = await self._req("POST", f"/{table}", json=data)
        except PostgRESTError as exc:
            if exc.status_code != 403:
                raise
            # PostgREST rolls back INSERT when return=representation is blocked by
            # SELECT RLS. Retry with return=minimal so the row is committed.
            await self._req(
                "POST",
                f"/{table}",
                json=data,
                prefer="return=minimal",
            )
            return {}
        if isinstance(result, list):
            return result[0] if result else {}
        return result or {}

    async def upsert(self, table: str, data: dict, on_conflict: str = "") -> dict | None:
        prefer = f"return=representation,resolution=merge-duplicates"
        params = {"on_conflict": on_conflict} if on_conflict else None
        result = await self._req("POST", f"/{table}", json=data, params=params, prefer=prefer)
        if isinstance(result, list):
            return result[0] if result else None
        return result

    async def update(self, table: str, filters: dict, data: dict) -> dict | None:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        try:
            result = await self._req("PATCH", f"/{table}", params=params, json=data)
        except PostgRESTError as exc:
            if exc.status_code != 403:
                raise
            await self._req(
                "PATCH",
                f"/{table}",
                params=params,
                json=data,
                prefer="return=minimal",
            )
            rows = await self.select(table, {**params, "limit": "1"})
            return rows[0] if rows else None
        if isinstance(result, list):
            return result[0] if result else None
        return result

    async def delete(self, table: str, filters: dict) -> int:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        result = await self._req("DELETE", f"/{table}", params=params, prefer="return=minimal")
        return 1  # PostgREST returns 204 on success

    async def rpc(self, func: str, params: dict) -> Any:
        result = await self._req("POST", f"/rpc/{func}", json=params, prefer="")
        return result


def db(jwt: str) -> PostgREST:
    """Factory used in route handlers: ``client = db(user['_token'])``."""
    return PostgREST(jwt)
