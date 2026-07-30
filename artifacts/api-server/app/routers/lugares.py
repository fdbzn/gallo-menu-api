"""Módulo 8 — Lugares de compra."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(prefix="/lugares_compra", tags=["lugares"])


class LugarBody(BaseModel):
    nombre: str


@router.get("")
async def list_lugares(user: dict = Depends(get_current_user)):
    return await db(user["_token"]).select(
        "lugares_compra",
        {"creador_id": f"eq.{user['sub']}", "order": "nombre.asc"},
    )


@router.post("", status_code=201)
async def create_lugar(body: LugarBody, user: dict = Depends(get_current_user)):
    return await db(user["_token"]).insert(
        "lugares_compra", {"creador_id": user["sub"], "nombre": body.nombre}
    )


@router.patch("/{lugar_id}")
async def update_lugar(lugar_id: str, body: LugarBody, user: dict = Depends(get_current_user)):
    row = await db(user["_token"]).update("lugares_compra", {"id": lugar_id}, {"nombre": body.nombre})
    if not row:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")
    return row


@router.delete("/{lugar_id}", status_code=204)
async def delete_lugar(lugar_id: str, user: dict = Depends(get_current_user)):
    await db(user["_token"]).delete("lugares_compra", {"id": lugar_id})
