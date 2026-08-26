"""Módulo 4 — Mesas de trabajo y compartición."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(prefix="/mesas_trabajo", tags=["mesas"])
# Share routes at API root (/mesa_compartida) — same pattern as menu_compartido
compartir_router = APIRouter(tags=["mesas"])


class MesaBody(BaseModel):
    nombre: str


class CompartirMesaBody(BaseModel):
    mesa_id: str
    usuario_invitado_id: str
    tipo_cuenta_id: Optional[int] = None


class ResponderMesaBody(BaseModel):
    estado: str  # "aceptado" | "denegado"


class CambiarRolMesaBody(BaseModel):
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


@router.get("")
async def list_mesas(user: dict = Depends(get_current_user)):
    # Nest creator profile so invitees see "Por {nombre}" instead of "Por Usuario"
    return await db(user["_token"]).select(
        "mesas_trabajo",
        {
            "select": "*,perfiles:creador_id(id,nombre)",
            "order": "created_at.desc",
        },
    )


@router.post("", status_code=201)
async def create_mesa(body: MesaBody, user: dict = Depends(get_current_user)):
    client = db(user["_token"])
    row = await client.insert(
        "mesas_trabajo", {"creador_id": user["sub"], "nombre": body.nombre}
    )
    
    mesa_id = row.get("id")
    if not mesa_id:
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
            row = rows[0]
            mesa_id = row.get("id")
        else:
            raise HTTPException(status_code=403, detail="No se pudo crear la mesa")

    # Crear lugares por defecto
    for idx, lugar in enumerate(["Walmart", "Mercado", "Sam's Club"]):
        await client.insert(
            "lugares_compra",
            {
                "creador_id": user["sub"],
                "nombre": lugar,
                "mesa_id": mesa_id,
                "orden": idx
            }
        )

    # Crear agrupadores por defecto
    for idx, segmento in enumerate(["Desayuno", "Comida", "Cena", "Postre", "Otro"]):
        await client.insert(
            "segmentos_menu",
            {
                "creador_id": user["sub"],
                "nombre": segmento,
                "mesa_id": mesa_id,
                "orden": idx
            }
        )

    return row


@router.patch("/{mesa_id}")
async def update_mesa(mesa_id: str, body: MesaBody, user: dict = Depends(get_current_user)):
    row = await db(user["_token"]).update("mesas_trabajo", {"id": mesa_id}, {"nombre": body.nombre})
    if not row:
        raise HTTPException(status_code=404, detail="Mesa no encontrada o sin permiso")
    return row


@router.delete("/{mesa_id}", status_code=204)
async def delete_mesa(mesa_id: str, user: dict = Depends(get_current_user)):
    await db(user["_token"]).delete("mesas_trabajo", {"id": mesa_id})


# ── Compartición de mesa ──────────────────────────────────────────────────────

@compartir_router.get("/mesa_compartida")
async def list_mesa_compartida(
    mesa_id: str = Query(...),
    user: dict = Depends(get_current_user),
):
    return await db(user["_token"]).select(
        "mesa_compartida",
        {
            "mesa_id": f"eq.{mesa_id}",
            "select": "*,cat_tipos_cuenta(id,codigo,nombre)",
            "order": "created_at.desc",
        },
    )


@compartir_router.get("/mesa_compartida/pendientes")
async def list_pending_mesa_invitations(user: dict = Depends(get_current_user)):
    return await db(user["_token"]).rpc("list_pending_mesa_invitations", {})


@compartir_router.post("/mesa_compartida", status_code=201)
async def compartir_mesa(body: CompartirMesaBody, user: dict = Depends(get_current_user)):
    tipo_cuenta_id = await _resolve_tipo_cuenta_id(user["_token"], body.tipo_cuenta_id)
    return await db(user["_token"]).insert(
        "mesa_compartida",
        {
            "mesa_id": body.mesa_id,
            "usuario_invitado_id": body.usuario_invitado_id,
            "tipo_cuenta_id": tipo_cuenta_id,
        },
    )


@compartir_router.patch("/mesa_compartida/{mesa_id}")
async def responder_invitacion_mesa(
    mesa_id: str, body: ResponderMesaBody, user: dict = Depends(get_current_user)
):
    if body.estado == "denegado":
        await db(user["_token"]).delete(
            "mesa_compartida",
            {"mesa_id": mesa_id, "usuario_invitado_id": user["sub"]},
        )
        return {"detail": "Invitación rechazada"}
    row = await db(user["_token"]).update(
        "mesa_compartida",
        {"mesa_id": mesa_id, "usuario_invitado_id": user["sub"]},
        {"estado": body.estado},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    return row


@compartir_router.patch("/mesa_compartida/{mesa_id}/usuario/{usuario_id}/rol")
async def cambiar_rol_mesa(
    mesa_id: str,
    usuario_id: str,
    body: CambiarRolMesaBody,
    user: dict = Depends(get_current_user),
):
    """Propietario (invite_manage): editor ↔ solo_ver. No asigna propietario."""
    tipo_cuenta_id = await _resolve_tipo_cuenta_id(user["_token"], body.tipo_cuenta_id)
    row = await db(user["_token"]).update(
        "mesa_compartida",
        {"mesa_id": mesa_id, "usuario_invitado_id": usuario_id},
        {"tipo_cuenta_id": tipo_cuenta_id},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    return row


@compartir_router.delete("/mesa_compartida/{mesa_id}/usuario/{usuario_id}", status_code=204)
async def revocar_acceso_mesa(
    mesa_id: str, usuario_id: str, user: dict = Depends(get_current_user)
):
    await db(user["_token"]).delete(
        "mesa_compartida",
        {"mesa_id": mesa_id, "usuario_invitado_id": usuario_id},
    )
