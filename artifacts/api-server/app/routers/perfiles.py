"""Módulo 0 — Perfil y búsqueda de usuarios."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import db
from app.deps import get_current_user

router = APIRouter(prefix="/perfiles", tags=["perfiles"])

Genero = Literal["hombre", "mujer", "otro"]


class PatchPerfil(BaseModel):
    nombre: Optional[str] = None
    nombres: Optional[str] = Field(default=None, min_length=1)
    apellidos: Optional[str] = None
    telefono: Optional[str] = None
    genero: Optional[Genero] = None


def _display_nombre(nombres: str, apellidos: str) -> str:
    return " ".join(part for part in (nombres.strip(), apellidos.strip()) if part)


@router.get("/me")
async def get_my_profile(user: dict = Depends(get_current_user)):
    row = await db(user["_token"]).select_one("perfiles", {"id": f"eq.{user['sub']}"})
    if not row:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return row


@router.patch("/me")
async def update_my_profile(body: PatchPerfil, user: dict = Depends(get_current_user)):
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Nada que actualizar")

    current = await db(user["_token"]).select_one("perfiles", {"id": f"eq.{user['sub']}"})
    if not current:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    if "nombres" in payload or "apellidos" in payload:
        nombres = str(payload.get("nombres", current.get("nombres") or current.get("nombre") or "")).strip()
        apellidos = str(payload.get("apellidos", current.get("apellidos") or "")).strip()
        if "nombres" in payload:
            payload["nombres"] = nombres
        if "apellidos" in payload:
            payload["apellidos"] = apellidos
        payload["nombre"] = _display_nombre(nombres, apellidos)
    elif "nombre" in payload and payload["nombre"] is not None:
        payload["nombre"] = str(payload["nombre"]).strip()

    if "telefono" in payload and payload["telefono"] is not None:
        payload["telefono"] = str(payload["telefono"]).strip() or None

    row = await db(user["_token"]).update("perfiles", {"id": user["sub"]}, payload)
    if not row:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return row


@router.get("/buscar")
async def search_users(
    q: str = Query(..., min_length=1),
    user: dict = Depends(get_current_user),
):
    """Buscar usuarios — amigos aparecen primero (regla 6.4)."""
    rows = await db(user["_token"]).select(
        "perfiles",
        {
            "nombre": f"ilike.*{q}*",
            "id": f"neq.{user['sub']}",
            "limit": "20",
            "select": "id,nombre,created_at",
        },
    )
    friends_raw = await db(user["_token"]).select(
        "amigos", {"usuario_id": f"eq.{user['sub']}", "select": "amigo_id"}
    )
    friend_ids = {f["amigo_id"] for f in friends_raw}
    for r in rows:
        r["es_amigo"] = r["id"] in friend_ids
    rows.sort(key=lambda r: (not r["es_amigo"], r.get("nombre", "")))
    return rows
