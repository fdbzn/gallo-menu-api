"""Módulo Siguiente Compra — Items diferidos para la siguiente compra."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(tags=["siguiente_compra"])


class CreateSiguienteCompraBody(BaseModel):
    mesa_id: str
    ingrediente_id: str
    lugar_compra_id: Optional[str] = None
    cantidad: Optional[str] = None
    notas: Optional[str] = None


class UpdateSiguienteCompraBody(BaseModel):
    lugar_compra_id: Optional[str] = None
    cantidad: Optional[str] = None
    notas: Optional[str] = None


class TransferirSiguienteCompraBody(BaseModel):
    lista_compra_id: str
    items: list[dict]  # list of { ingrediente_id, lugar_compra_id, cantidad }
    item_ids: list[str]  # ids to delete from siguiente_compra


class DescartarSiguienteCompraBody(BaseModel):
    item_ids: list[str]


@router.get("/siguiente_compra")
async def get_siguiente_compra(
    mesa_id: str = Query(..., description="ID de la mesa de trabajo"),
    user: dict = Depends(get_current_user),
):
    """Lista todos los items marcados para siguiente compra en una mesa."""
    rows = await db(user["_token"]).select(
        "siguiente_compra",
        {
            "mesa_id": f"eq.{mesa_id}",
            "select": "*,ingredientes(nombre,categoria),lugares_compra(nombre)",
            "order": "created_at.desc",
        },
    )
    return rows


@router.post("/siguiente_compra")
async def add_siguiente_compra(
    body: CreateSiguienteCompraBody,
    user: dict = Depends(get_current_user),
):
    """Agrega o actualiza un item en la lista de siguiente compra."""
    data = {
        "mesa_id": body.mesa_id,
        "creador_id": user["sub"],
        "ingrediente_id": body.ingrediente_id,
        "lugar_compra_id": body.lugar_compra_id,
        "cantidad": body.cantidad,
        "notas": body.notas,
    }
    # Insert or upsert via db
    row = await db(user["_token"]).upsert("siguiente_compra", data, on_conflict="mesa_id,ingrediente_id")
    return row


@router.patch("/siguiente_compra/{item_id}")
async def update_siguiente_compra(
    item_id: str,
    body: UpdateSiguienteCompraBody,
    user: dict = Depends(get_current_user),
):
    """Actualiza cantidad, lugar o notas de un item en siguiente compra."""
    payload = {}
    if body.cantidad is not None:
        payload["cantidad"] = body.cantidad
    if body.lugar_compra_id is not None:
        payload["lugar_compra_id"] = body.lugar_compra_id
    if body.notas is not None:
        payload["notas"] = body.notas

    row = await db(user["_token"]).update("siguiente_compra", {"id": item_id}, payload)
    if not row:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return row


@router.delete("/siguiente_compra/{item_id}")
async def delete_siguiente_compra(
    item_id: str,
    user: dict = Depends(get_current_user),
):
    """Elimina un item individual de siguiente compra."""
    await db(user["_token"]).delete("siguiente_compra", {"id": item_id})
    return {"status": "ok"}


@router.post("/siguiente_compra/transferir")
async def transferir_siguiente_compra(
    body: TransferirSiguienteCompraBody,
    user: dict = Depends(get_current_user),
):
    """Inserta los items en la lista de compra indicada y los remueve de siguiente_compra."""
    client = db(user["_token"])

    # Insert items in lista_compra_items
    for it in body.items:
        await client.insert(
            "lista_compra_items",
            {
                "lista_compra_id": body.lista_compra_id,
                "ingrediente_id": it["ingrediente_id"],
                "lugar_compra_id": it.get("lugar_compra_id"),
                "cantidad": it.get("cantidad"),
                "agregado_manualmente": True,
                "estado": "pendiente",
                "orden": it.get("orden", 0),
            },
        )

    # Delete from siguiente_compra
    for item_id in body.item_ids:
        await client.delete("siguiente_compra", {"id": item_id})

    return {"status": "ok", "transferred_count": len(body.item_ids)}


@router.post("/siguiente_compra/descartar")
async def descartar_siguiente_compra(
    body: DescartarSiguienteCompraBody,
    user: dict = Depends(get_current_user),
):
    """Elimina en lote los items de siguiente compra que fueron rechazados."""
    client = db(user["_token"])
    for item_id in body.item_ids:
        await client.delete("siguiente_compra", {"id": item_id})
    return {"status": "ok", "deleted_count": len(body.item_ids)}
