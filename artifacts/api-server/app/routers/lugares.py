"""Módulo 8 — Lugares de compra."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(prefix="/lugares_compra", tags=["lugares"])
rpc_router = APIRouter(tags=["lugares"])

class BulkReorderBody(BaseModel):
    p_items: list[dict]

@rpc_router.post("/rpc/reorder_lugares_compra")
async def bulk_reorder_lugares(body: BulkReorderBody, user: dict = Depends(get_current_user)):
    await db(user["_token"]).rpc(
        "reorder_lugares_compra",
        {"p_items": body.p_items},
    )
    return {"status": "ok"}


class LugarBody(BaseModel):
    nombre: str
    mesa_id: Optional[str] = None


class CreateLugarBody(BaseModel):
    nombre: str
    mesa_id: str


@router.get("")
async def list_lugares(
    user: dict = Depends(get_current_user),
    mesa_id: Optional[str] = Query(None, description="Filtra por mesa"),
):
    if not mesa_id:
        raise HTTPException(status_code=400, detail="mesa_id es requerido")
    return await db(user["_token"]).select(
        "lugares_compra",
        {"mesa_id": f"eq.{mesa_id}", "order": "orden.asc,nombre.asc"},
    )


@router.post("", status_code=201)
async def create_lugar(body: CreateLugarBody, user: dict = Depends(get_current_user)):
    return await db(user["_token"]).insert(
        "lugares_compra",
        {"creador_id": user["sub"], "nombre": body.nombre, "mesa_id": body.mesa_id},
    )


class UpdateLugarBody(BaseModel):
    nombre: str


class ReorderLugarBody(BaseModel):
    orden: int


@router.patch("/{lugar_id}")
async def update_lugar(lugar_id: str, body: UpdateLugarBody, user: dict = Depends(get_current_user)):
    row = await db(user["_token"]).update("lugares_compra", {"id": lugar_id}, {"nombre": body.nombre})
    if not row:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")
    return row


@router.patch("/{lugar_id}/orden")
async def reorder_lugar(lugar_id: str, body: ReorderLugarBody, user: dict = Depends(get_current_user)):
    row = await db(user["_token"]).update("lugares_compra", {"id": lugar_id}, {"orden": body.orden})
    if not row:
        raise HTTPException(status_code=404, detail="Lugar no encontrado")
    return row


@router.delete("/{lugar_id}", status_code=204)
async def delete_lugar(lugar_id: str, user: dict = Depends(get_current_user)):
    await db(user["_token"]).delete("lugares_compra", {"id": lugar_id})
