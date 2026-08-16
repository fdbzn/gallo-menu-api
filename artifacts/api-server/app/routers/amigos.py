"""Módulo 6 — Amigos / Invitados a la mesa."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(prefix="/amigos", tags=["amigos"])


class AgregarAmigoBody(BaseModel):
    p_amigo_id: str


@router.get("")
async def list_amigos(user: dict = Depends(get_current_user)):
    return await db(user["_token"]).select(
        "amigos",
        {
            "usuario_id": f"eq.{user['sub']}",
            "select": "*,perfiles:amigo_id(id,nombre)",
        },
    )


@router.post("/agregar", status_code=201)
async def agregar_amigo(body: AgregarAmigoBody, user: dict = Depends(get_current_user)):
    await db(user["_token"]).rpc("agregar_amigo", {"p_amigo_id": body.p_amigo_id})
    return {"detail": "Amistad creada"}


@router.delete("/{amigo_id}", status_code=204)
async def quitar_amigo(amigo_id: str, user: dict = Depends(get_current_user)):
    await db(user["_token"]).rpc("quitar_amigo", {"p_amigo_id": amigo_id})


@router.get("/check/{amigo_id}")
async def check_amistad(amigo_id: str, user: dict = Depends(get_current_user)):
    rows = await db(user["_token"]).select(
        "amigos",
        {"usuario_id": f"eq.{user['sub']}", "amigo_id": f"eq.{amigo_id}"},
    )
    return {"es_amigo": len(rows) > 0}
