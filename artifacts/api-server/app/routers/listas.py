"""Módulo 8 — Listas de compras."""
from typing import Literal, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.database import db
from app.deps import get_current_user

router = APIRouter(tags=["listas"])

class BulkReorderListasBody(BaseModel):
    p_lista_id: str
    p_items: list[dict]

@router.post("/rpc/reorder_lista_compra_items")
async def bulk_reorder_listas(body: BulkReorderListasBody, user: dict = Depends(get_current_user)):
    await db(user["_token"]).rpc(
        "reorder_lista_compra_items",
        {"p_lista_id": body.p_lista_id, "p_items": body.p_items},
    )
    return {"status": "ok"}


class RenameListaBody(BaseModel):
    nombre: str


class SetEstadoBody(BaseModel):
    estado: Literal["pendiente", "no_adquirido", "adquirido"]


class MoveToLugarBody(BaseModel):
    lugar_compra_id: Optional[str] = None


class ReorderItemBody(BaseModel):
    orden: int


class AddItemManualBody(BaseModel):
    lista_compra_id: str
    ingrediente_id: str
    agregado_manualmente: bool = True
    lugar_compra_id: Optional[str] = None


class AssignItemPlatilloBody(BaseModel):
    item_id: str
    platillo_id: str


class AssignItemPlatilloNuevoBody(BaseModel):
    item_id: str
    nombre: str
    tipos: list[str] = []


# ── Lista ──────────────────────────────────────────────────────────────────────

@router.get("/listas_compras")
async def get_lista_by_menu(menu_id: str, user: dict = Depends(get_current_user)):
    """GET lista con items y sus platillos (regla 8.4)."""
    rows = await db(user["_token"]).select(
        "listas_compras",
        {
            "menu_id": f"eq.{menu_id}",
            "select": "*,lista_compra_items(*,lista_compra_item_platillos(platillo_id,platillos(nombre)),ingredientes(nombre),lugares_compra(nombre))",
        },
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    return rows[0]


@router.patch("/listas_compras/{lista_id}")
async def rename_lista(lista_id: str, body: RenameListaBody, user: dict = Depends(get_current_user)):
    """Única mutación permitida sobre la lista como entidad (regla 8.3)."""
    row = await db(user["_token"]).update("listas_compras", {"id": lista_id}, {"nombre": body.nombre})
    if not row:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    return row


# ── Items ─────────────────────────────────────────────────────────────────────

@router.patch("/lista_compra_items/{item_id}/estado")
async def set_estado(
    item_id: str, body: SetEstadoBody, user: dict = Depends(get_current_user)
):
    """Actualiza el estado de adquisición de un item (pendiente / no_adquirido / adquirido)."""
    row = await db(user["_token"]).update(
        "lista_compra_items", {"id": item_id}, {"estado": body.estado}
    )
    if not row:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return row


@router.patch("/lista_compra_items/{item_id}/lugar")
async def move_to_lugar(
    item_id: str, body: MoveToLugarBody, user: dict = Depends(get_current_user)
):
    """null = sección sin lugar (regla 8.7)."""
    row = await db(user["_token"]).update(
        "lista_compra_items", {"id": item_id}, {"lugar_compra_id": body.lugar_compra_id}
    )
    if not row:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return row


@router.patch("/lista_compra_items/{item_id}/orden")
async def reorder_item(
    item_id: str, body: ReorderItemBody, user: dict = Depends(get_current_user)
):
    row = await db(user["_token"]).update(
        "lista_compra_items", {"id": item_id}, {"orden": body.orden}
    )
    if not row:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return row


@router.post("/lista_compra_items", status_code=201)
async def add_item_manual(body: AddItemManualBody, user: dict = Depends(get_current_user)):
    """Items sueltos sobreviven aunque se quiten platillos (regla 8.9)."""
    return await db(user["_token"]).insert(
        "lista_compra_items",
        {
            "lista_compra_id": body.lista_compra_id,
            "ingrediente_id": body.ingrediente_id,
            "agregado_manualmente": body.agregado_manualmente,
            "lugar_compra_id": body.lugar_compra_id,
        },
    )


@router.delete("/lista_compra_items/{item_id}", status_code=204)
async def remove_item_manual(item_id: str, user: dict = Depends(get_current_user)):
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {user['_token']}",
        "Prefer": "return=minimal",
    }
    async with httpx.AsyncClient(timeout=20) as http:
        resp = await http.delete(
            f"{settings.supabase_url}/rest/v1/lista_compra_items",
            headers=headers,
            params={"id": f"eq.{item_id}", "agregado_manualmente": "eq.true"},
        )
    resp.raise_for_status()


# ── RPCs ──────────────────────────────────────────────────────────────────────

@router.post("/rpc/assign_lista_item_platillo")
async def assign_item_platillo_existente(
    body: AssignItemPlatilloBody, user: dict = Depends(get_current_user)
):
    """Asignar item a platillo existente (reglas 8.11, 8.12)."""
    await db(user["_token"]).rpc(
        "assign_lista_item_platillo", {"p_item_id": body.item_id, "p_platillo_id": body.platillo_id}
    )
    return {"detail": "Asignado correctamente"}


@router.post("/rpc/assign_lista_item_platillo_nuevo", status_code=201)
async def assign_item_platillo_nuevo(
    body: AssignItemPlatilloNuevoBody, user: dict = Depends(get_current_user)
):
    """Crea platillo + tipos + asigna (regla 8.12)."""
    await db(user["_token"]).rpc(
        "assign_lista_item_platillo_nuevo",
        {"p_item_id": body.item_id, "p_nombre": body.nombre, "p_tipos": body.tipos},
    )
    return {"detail": "Platillo creado y asignado"}
