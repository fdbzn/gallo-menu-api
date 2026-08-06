"""Módulo 9 — Encuestas."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(tags=["encuestas"])


class CreateEncuestaBody(BaseModel):
    titulo: str


class UpdateEncuestaBody(BaseModel):
    titulo: Optional[str] = None
    estado: Optional[str] = None
    fecha_cierre: Optional[str] = None


class OpcionBody(BaseModel):
    encuesta_id: str
    platillo_id: str


class VotarBody(BaseModel):
    encuesta_id: str
    opcion_id: str


class CompartirEncuestaBody(BaseModel):
    encuesta_id: str
    usuario_id: str
    tipo_cuenta_id: Optional[int] = None  # editor | solo_ver; default solo_ver


class ResponderEncuestaBody(BaseModel):
    estado: str  # "aceptada" | "rechazada"


class CambiarRolEncuestaBody(BaseModel):
    tipo_cuenta_id: Optional[int] = None  # editor | solo_ver


async def _resolve_tipo_cuenta_id(token: str, tipo_cuenta_id: Optional[int]) -> int:
    if tipo_cuenta_id is not None:
        return tipo_cuenta_id
    rows = await db(token).select(
        "cat_tipos_cuenta",
        {"codigo": "eq.solo_ver", "select": "id", "limit": "1"},
    )
    if rows:
        return rows[0]["id"]
    return 3


# ── Encuestas ─────────────────────────────────────────────────────────────────

@router.get("/encuestas")
async def list_encuestas(user: dict = Depends(get_current_user)):
    return await db(user["_token"]).select(
        "encuestas",
        {
            "select": "*,encuesta_opciones(*,platillos(nombre)),encuesta_compartida(*,cat_tipos_cuenta(id,codigo,nombre)),encuesta_votos(*)",
            "order": "created_at.desc",
        },
    )


@router.post("/encuestas", status_code=201)
async def create_encuesta(body: CreateEncuestaBody, user: dict = Depends(get_current_user)):
    return await db(user["_token"]).insert(
        "encuestas", {"creador_id": user["sub"], "titulo": body.titulo}
    )


@router.patch("/encuestas/{encuesta_id}")
async def update_encuesta(
    encuesta_id: str, body: UpdateEncuestaBody, user: dict = Depends(get_current_user)
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        rows = await db(user["_token"]).select("encuestas", {"id": f"eq.{encuesta_id}"})
        return rows[0] if rows else {}
    row = await db(user["_token"]).update("encuestas", {"id": encuesta_id}, data)
    if not row:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada o sin permiso")
    return row


@router.delete("/encuestas/{encuesta_id}", status_code=204)
async def delete_encuesta(encuesta_id: str, user: dict = Depends(get_current_user)):
    await db(user["_token"]).delete("encuestas", {"id": encuesta_id})


# ── Opciones ──────────────────────────────────────────────────────────────────

@router.post("/encuesta_opciones", status_code=201)
async def add_opcion(body: OpcionBody, user: dict = Depends(get_current_user)):
    return await db(user["_token"]).insert(
        "encuesta_opciones", {"encuesta_id": body.encuesta_id, "platillo_id": body.platillo_id}
    )


@router.delete("/encuesta_opciones/{opcion_id}", status_code=204)
async def remove_opcion(opcion_id: str, user: dict = Depends(get_current_user)):
    await db(user["_token"]).delete("encuesta_opciones", {"id": opcion_id})


# ── Votos ─────────────────────────────────────────────────────────────────────

@router.post("/rpc/votar_encuesta")
async def votar_encuesta(body: VotarBody, user: dict = Depends(get_current_user)):
    """Toggle si misma opción; cambio si otra; insert si ninguna."""
    await db(user["_token"]).rpc(
        "votar_encuesta", {"p_encuesta_id": body.encuesta_id, "p_opcion_id": body.opcion_id}
    )
    return {"detail": "Voto registrado"}


@router.get("/encuesta_votos")
async def get_votos(encuesta_id: str, user: dict = Depends(get_current_user)):
    return await db(user["_token"]).select(
        "encuesta_votos", {"encuesta_id": f"eq.{encuesta_id}"}
    )


# ── Compartición ──────────────────────────────────────────────────────────────

@router.post("/encuesta_compartida", status_code=201)
async def compartir_encuesta(
    body: CompartirEncuestaBody, user: dict = Depends(get_current_user)
):
    """Trigger crea amistad automáticamente (regla 6.3)."""
    tipo_cuenta_id = await _resolve_tipo_cuenta_id(user["_token"], body.tipo_cuenta_id)
    return await db(user["_token"]).insert(
        "encuesta_compartida",
        {
            "encuesta_id": body.encuesta_id,
            "usuario_id": body.usuario_id,
            "tipo_cuenta_id": tipo_cuenta_id,
        },
    )


@router.patch("/encuesta_compartida/{encuesta_id}")
async def responder_invitacion_encuesta(
    encuesta_id: str, body: ResponderEncuestaBody, user: dict = Depends(get_current_user)
):
    if body.estado == "rechazada":
        await db(user["_token"]).delete(
            "encuesta_compartida", {"encuesta_id": encuesta_id, "usuario_id": user["sub"]}
        )
        return {"detail": "Invitación rechazada"}
    row = await db(user["_token"]).update(
        "encuesta_compartida",
        {"encuesta_id": encuesta_id, "usuario_id": user["sub"]},
        {"estado": body.estado},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    return row


@router.patch("/encuesta_compartida/{encuesta_id}/usuario/{usuario_id}/rol")
async def cambiar_rol_encuesta(
    encuesta_id: str,
    usuario_id: str,
    body: CambiarRolEncuestaBody,
    user: dict = Depends(get_current_user),
):
    """Propietario (invite_manage): editor ↔ solo_ver. No asigna propietario."""
    tipo_cuenta_id = await _resolve_tipo_cuenta_id(user["_token"], body.tipo_cuenta_id)
    row = await db(user["_token"]).update(
        "encuesta_compartida",
        {"encuesta_id": encuesta_id, "usuario_id": usuario_id},
        {"tipo_cuenta_id": tipo_cuenta_id},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    return row


@router.delete(
    "/encuesta_compartida/{encuesta_id}/usuario/{usuario_id}", status_code=204
)
async def revocar_acceso_encuesta(
    encuesta_id: str, usuario_id: str, user: dict = Depends(get_current_user)
):
    await db(user["_token"]).delete(
        "encuesta_compartida",
        {"encuesta_id": encuesta_id, "usuario_id": usuario_id},
    )


@router.get("/encuesta_compartida/pendientes")
async def list_pending_encuesta_invitations(user: dict = Depends(get_current_user)):
    return await db(user["_token"]).rpc("list_pending_encuesta_invitations", {})
