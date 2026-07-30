"""Módulo 0 — Perfil y búsqueda de usuarios."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(prefix="/perfiles", tags=["perfiles"])


class PatchPerfil(BaseModel):
    nombre: str


@router.get("/me")
async def get_my_profile(user: dict = Depends(get_current_user)):
    row = await db(user["_token"]).select_one("perfiles", {"id": f"eq.{user['sub']}"})
    if not row:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return row


@router.patch("/me")
async def update_my_profile(body: PatchPerfil, user: dict = Depends(get_current_user)):
    row = await db(user["_token"]).update("perfiles", {"id": user["sub"]}, {"nombre": body.nombre})
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
    # Ordenar amigos primero en el cliente (regla 6.4)
    friends_raw = await db(user["_token"]).select(
        "amigos", {"usuario_id": f"eq.{user['sub']}", "select": "amigo_id"}
    )
    friend_ids = {f["amigo_id"] for f in friends_raw}
    for r in rows:
        r["es_amigo"] = r["id"] in friend_ids
    rows.sort(key=lambda r: (not r["es_amigo"], r.get("nombre", "")))
    return rows
