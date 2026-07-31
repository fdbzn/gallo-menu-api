"""Módulo 4 — Mesas de trabajo."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(prefix="/mesas_trabajo", tags=["mesas"])


class MesaBody(BaseModel):
    nombre: str


@router.get("")
async def list_mesas(user: dict = Depends(get_current_user)):
    return await db(user["_token"]).select("mesas_trabajo", {"order": "created_at.desc"})


@router.post("", status_code=201)
async def create_mesa(body: MesaBody, user: dict = Depends(get_current_user)):
    client = db(user["_token"])
    row = await client.insert(
        "mesas_trabajo", {"creador_id": user["sub"], "nombre": body.nombre}
    )
    if row.get("id"):
        return row
    rows = await client.select(
        "mesas_trabajo",
        {
            "creador_id": f"eq.{user['sub']}",
            "nombre": f"eq.{body.nombre}",
            "order": "created_at.desc",
            "limit": "1",
        },
    )
    if rows:
        return rows[0]
    raise HTTPException(status_code=500, detail="No se pudo crear la mesa")


@router.patch("/{mesa_id}")
async def update_mesa(mesa_id: str, body: MesaBody, user: dict = Depends(get_current_user)):
    row = await db(user["_token"]).update("mesas_trabajo", {"id": mesa_id}, {"nombre": body.nombre})
    if not row:
        raise HTTPException(status_code=404, detail="Mesa no encontrada o sin permiso")
    return row


@router.delete("/{mesa_id}", status_code=204)
async def delete_mesa(mesa_id: str, user: dict = Depends(get_current_user)):
    await db(user["_token"]).delete("mesas_trabajo", {"id": mesa_id})
