"""Módulo 5.5 — Agrupadores/Segmentos de menú."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(tags=["segmentos"])


class SegmentoBody(BaseModel):
    mesa_trabajo_id: str
    nombre: str


class SegmentoUpdateBody(BaseModel):
    nombre: str


class ReorderSegmentoBody(BaseModel):
    orden: int


@router.get("/segmentos_menu")
async def list_segmentos(mesa_trabajo_id: str, user: dict = Depends(get_current_user)):
    return await db(user["_token"]).select(
        "segmentos_menu",
        {
            "mesa_id": f"eq.{mesa_trabajo_id}",
            "order": "created_at.asc",
        },
    )


@router.post("/segmentos_menu", status_code=201)
async def create_segmento(body: SegmentoBody, user: dict = Depends(get_current_user)):
    return await db(user["_token"]).insert(
        "segmentos_menu",
        {
            "mesa_id": body.mesa_trabajo_id,
            "creador_id": user["sub"],
            "nombre": body.nombre,
        },
    )


@router.patch("/segmentos_menu/{segmento_id}")
async def update_segmento(
    segmento_id: str, body: SegmentoUpdateBody, user: dict = Depends(get_current_user)
):
    row = await db(user["_token"]).update(
        "segmentos_menu", {"id": segmento_id}, {"nombre": body.nombre}
    )
    if not row:
        raise HTTPException(status_code=404, detail="Segmento no encontrado")
    return row


@router.patch("/segmentos_menu/{segmento_id}/orden")
async def reorder_segmento(
    segmento_id: str, body: ReorderSegmentoBody, user: dict = Depends(get_current_user)
):
    row = await db(user["_token"]).update(
        "segmentos_menu", {"id": segmento_id}, {"orden": body.orden}
    )
    if not row:
        raise HTTPException(status_code=404, detail="Segmento no encontrado")
    return row


@router.delete("/segmentos_menu/{segmento_id}", status_code=204)
async def delete_segmento(segmento_id: str, user: dict = Depends(get_current_user)):
    await db(user["_token"]).delete("segmentos_menu", {"id": segmento_id})
