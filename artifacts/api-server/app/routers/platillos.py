"""Módulo 7 — Platillos e ingredientes del platillo."""
from typing import List, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.database import db
from app.deps import get_current_user

router = APIRouter(tags=["platillos"])


def _as_postgrest_filter(value: str) -> str:
    if value.startswith(("eq.", "in.", "neq.", "gt.", "gte.", "lt.", "lte.", "like.", "ilike.")):
        return value
    return f"eq.{value}"


class CreatePlatilloBody(BaseModel):
    nombre: str
    tipos: List[int] = []


class UpdatePlatilloBody(BaseModel):
    nombre: Optional[str] = None
    tipos: Optional[List[int]] = None


class DeletePlatilloRPCBody(BaseModel):
    platillo_id: str
    ingrediente_ids_a_borrar: List[str] = []


class PlatilloIngredienteBody(BaseModel):
    platillo_id: str
    ingrediente_id: str
    cantidad: Optional[str] = None


class UpdateCantidadBody(BaseModel):
    cantidad: str


# ── Catálogo ──────────────────────────────────────────────────────────────────

@router.get("/cat_tipos_comida", tags=["catalogo"])
async def list_tipos_comida(user: dict = Depends(get_current_user)):
    return await db(user["_token"]).select("cat_tipos_comida", {"order": "id.asc"})


# ── Platillos ─────────────────────────────────────────────────────────────────

@router.get("/platillos")
async def list_platillos(
    user: dict = Depends(get_current_user),
    id: Optional[str] = Query(
        None,
        description="PostgREST id filter, e.g. in.(uuid1,uuid2) for shared-menu resolution",
    ),
):
    """
    Catálogo = solo propios.

    RLS también permite leer platillos de menús/encuestas compartidos; eso sigue
    válido vía `id=in.(...)`, pero el listado por defecto no los mezcla en el
    inventario del usuario.
    """
    params: dict[str, str] = {
        "select": (
            "*,platillo_tipos(tipo_comida_id),"
            "platillo_ingredientes(ingrediente_id,cantidad,ingredientes(id,nombre))"
        ),
        "order": "nombre.asc",
    }
    if id:
        params["id"] = _as_postgrest_filter(id)
    else:
        params["creador_id"] = f"eq.{user['sub']}"
    return await db(user["_token"]).select("platillos", params)


@router.post("/platillos", status_code=201)
async def create_platillo(body: CreatePlatilloBody, user: dict = Depends(get_current_user)):
    client = db(user["_token"])
    platillo = await client.insert("platillos", {"creador_id": user["sub"], "nombre": body.nombre})
    pid = platillo["id"]
    for tipo_id in body.tipos:
        await client.insert("platillo_tipos", {"platillo_id": pid, "tipo_comida_id": tipo_id})
    return platillo


@router.patch("/platillos/{platillo_id}")
async def update_platillo(
    platillo_id: str, body: UpdatePlatilloBody, user: dict = Depends(get_current_user)
):
    client = db(user["_token"])
    if body.nombre is not None:
        row = await client.update("platillos", {"id": platillo_id}, {"nombre": body.nombre})
        if not row:
            raise HTTPException(status_code=404, detail="Platillo no encontrado")
    if body.tipos is not None:
        # Reemplazar tipos: borrar y re-insertar
        headers = {
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {user['_token']}",
            "Prefer": "return=minimal",
        }
        async with httpx.AsyncClient(timeout=20) as http:
            await http.delete(
                f"{settings.supabase_url}/rest/v1/platillo_tipos",
                headers=headers,
                params={"platillo_id": f"eq.{platillo_id}"},
            )
        for tipo_id in body.tipos:
            await client.insert("platillo_tipos", {"platillo_id": platillo_id, "tipo_comida_id": tipo_id})
    rows = await client.select("platillos", {"id": f"eq.{platillo_id}"})
    return rows[0] if rows else {}


@router.delete("/platillos/{platillo_id}", status_code=204)
async def delete_platillo_simple(platillo_id: str, user: dict = Depends(get_current_user)):
    await db(user["_token"]).delete("platillos", {"id": platillo_id})


@router.post("/rpc/delete_platillo", status_code=204)
async def delete_platillo_selectivo(
    body: DeletePlatilloRPCBody, user: dict = Depends(get_current_user)
):
    """Regla 7.6 — pregunta qué ingredientes sin otros platillos eliminar."""
    await db(user["_token"]).rpc(
        "delete_platillo",
        {"p_platillo_id": body.platillo_id, "p_ingrediente_ids_a_borrar": body.ingrediente_ids_a_borrar},
    )


# ── Ingredientes del platillo ─────────────────────────────────────────────────

@router.post("/platillo_ingredientes", status_code=201)
async def add_ingrediente_to_platillo(
    body: PlatilloIngredienteBody, user: dict = Depends(get_current_user)
):
    """Trigger sincroniza listas de compras automáticamente."""
    return await db(user["_token"]).insert(
        "platillo_ingredientes",
        {"platillo_id": body.platillo_id, "ingrediente_id": body.ingrediente_id, "cantidad": body.cantidad},
    )


@router.patch("/platillo_ingredientes")
async def update_ingrediente_cantidad(
    platillo_id: str,
    ingrediente_id: str,
    body: UpdateCantidadBody,
    user: dict = Depends(get_current_user),
):
    row = await db(user["_token"]).update(
        "platillo_ingredientes",
        {"platillo_id": platillo_id, "ingrediente_id": ingrediente_id},
        {"cantidad": body.cantidad},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Relación no encontrada")
    return row


@router.delete("/platillo_ingredientes", status_code=204)
async def remove_ingrediente_from_platillo(
    platillo_id: str, ingrediente_id: str, user: dict = Depends(get_current_user)
):
    """Trigger sincroniza listas de compras automáticamente."""
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {user['_token']}",
        "Prefer": "return=minimal",
    }
    async with httpx.AsyncClient(timeout=20) as http:
        resp = await http.delete(
            f"{settings.supabase_url}/rest/v1/platillo_ingredientes",
            headers=headers,
            params={"platillo_id": f"eq.{platillo_id}", "ingrediente_id": f"eq.{ingrediente_id}"},
        )
    resp.raise_for_status()
