"""Módulo 7 global — Ingredientes (inventario)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(prefix="/ingredientes", tags=["ingredientes"])


class CreateIngredienteBody(BaseModel):
    nombre: str
    categoria: Optional[str] = None
    stock: Optional[str] = None


class UpdateIngredienteBody(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    stock: Optional[str] = None


def _as_postgrest_filter(value: str) -> str:
    if value.startswith(("eq.", "in.", "neq.", "gt.", "gte.", "lt.", "lte.", "like.", "ilike.")):
        return value
    return f"eq.{value}"


@router.get("")
async def list_ingredientes(
    user: dict = Depends(get_current_user),
    id: Optional[str] = Query(
        None,
        description="PostgREST id filter, e.g. in.(uuid1,uuid2) for shared-menu resolution",
    ),
):
    """
    Catálogo de inventario = solo propios.

    RLS también permite leer ingredientes de menús compartidos; eso sigue
    válido vía `id=in.(...)` (detalle de platillo / lista), pero el listado
    por defecto no debe mezclarlos en el inventario del usuario.
    """
    params: dict[str, str] = {"order": "nombre.asc"}
    if id:
        params["id"] = _as_postgrest_filter(id)
    else:
        params["creador_id"] = f"eq.{user['sub']}"
    return await db(user["_token"]).select("ingredientes", params)


@router.post("", status_code=201)
async def create_ingrediente(body: CreateIngredienteBody, user: dict = Depends(get_current_user)):
    return await db(user["_token"]).insert(
        "ingredientes",
        {
            "creador_id": user["sub"],
            "nombre": body.nombre,
            "categoria": body.categoria,
            "stock": body.stock,
        },
    )


@router.patch("/{ingrediente_id}")
async def update_ingrediente(
    ingrediente_id: str, body: UpdateIngredienteBody, user: dict = Depends(get_current_user)
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        rows = await db(user["_token"]).select("ingredientes", {"id": f"eq.{ingrediente_id}"})
        return rows[0] if rows else {}
    row = await db(user["_token"]).update("ingredientes", {"id": ingrediente_id}, data)
    if not row:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    return row


@router.delete("/{ingrediente_id}", status_code=204)
async def delete_ingrediente(ingrediente_id: str, user: dict = Depends(get_current_user)):
    await db(user["_token"]).delete("ingredientes", {"id": ingrediente_id})
