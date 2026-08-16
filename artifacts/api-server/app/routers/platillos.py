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
    mesa_id: str
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


class CompartirPlatilloBody(BaseModel):
    platillo_id: str
    usuario_invitado_id: str
    tipo_cuenta_id: Optional[int] = None


class ResponderPlatilloBody(BaseModel):
    estado: str  # "aceptado" | "denegado"


class CambiarRolPlatilloBody(BaseModel):
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
    mesa_id: Optional[str] = Query(
        None,
        description="Filtra catálogo por mesa (requerido salvo resolución por id)",
    ),
    scope: Optional[str] = Query(
        None,
        description="catalogo = platillos de la mesa (RLS)",
    ),
):
    """
    Catálogo por mesa_id (RLS). Resolución puntual vía `id=in.(...)`.
    """
    client = db(user["_token"])
    select = (
        "*,platillo_tipos(tipo_comida_id),"
        "platillo_ingredientes(ingrediente_id,cantidad,ingredientes(id,nombre))"
    )
    if id:
        return await client.select(
            "platillos",
            {
                "id": _as_postgrest_filter(id),
                "select": select,
                "order": "nombre.asc",
            },
        )
    if not mesa_id:
        raise HTTPException(status_code=400, detail="mesa_id es requerido")
    return await client.select(
        "platillos",
        {
            "mesa_id": f"eq.{mesa_id}",
            "select": select,
            "order": "nombre.asc",
        },
    )


@router.post("/platillos", status_code=201)
async def create_platillo(body: CreatePlatilloBody, user: dict = Depends(get_current_user)):
    client = db(user["_token"])
    platillo = await client.insert(
        "platillos",
        {"creador_id": user["sub"], "nombre": body.nombre, "mesa_id": body.mesa_id},
    )
    pid = platillo.get("id")
    if not pid:
        rows = await client.select(
            "platillos",
            {
                "creador_id": f"eq.{user['sub']}",
                "nombre": f"eq.{body.nombre}",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        if not rows:
            raise HTTPException(
                status_code=403,
                detail="No se pudo crear el platillo (permisos RLS).",
            )
        platillo = rows[0]
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


# ── Compartición de platillo ──────────────────────────────────────────────────

@router.get("/platillo_compartido")
async def list_platillo_compartido(
    platillo_id: str = Query(...),
    user: dict = Depends(get_current_user),
):
    return await db(user["_token"]).select(
        "platillo_compartido",
        {
            "platillo_id": f"eq.{platillo_id}",
            "select": "*,cat_tipos_cuenta(id,codigo,nombre)",
            "order": "created_at.desc",
        },
    )


@router.get("/platillo_compartido/pendientes")
async def list_pending_platillo_invitations(user: dict = Depends(get_current_user)):
    return await db(user["_token"]).rpc("list_pending_platillo_invitations", {})


@router.post("/platillo_compartido", status_code=201)
async def compartir_platillo(
    body: CompartirPlatilloBody, user: dict = Depends(get_current_user)
):
    tipo_cuenta_id = await _resolve_tipo_cuenta_id(user["_token"], body.tipo_cuenta_id)
    return await db(user["_token"]).insert(
        "platillo_compartido",
        {
            "platillo_id": body.platillo_id,
            "usuario_invitado_id": body.usuario_invitado_id,
            "tipo_cuenta_id": tipo_cuenta_id,
        },
    )


@router.patch("/platillo_compartido/{platillo_id}")
async def responder_invitacion_platillo(
    platillo_id: str, body: ResponderPlatilloBody, user: dict = Depends(get_current_user)
):
    if body.estado == "denegado":
        await db(user["_token"]).delete(
            "platillo_compartido",
            {"platillo_id": platillo_id, "usuario_invitado_id": user["sub"]},
        )
        return {"detail": "Invitación rechazada"}
    row = await db(user["_token"]).update(
        "platillo_compartido",
        {"platillo_id": platillo_id, "usuario_invitado_id": user["sub"]},
        {"estado": body.estado},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    return row


@router.patch("/platillo_compartido/{platillo_id}/usuario/{usuario_id}/rol")
async def cambiar_rol_platillo(
    platillo_id: str,
    usuario_id: str,
    body: CambiarRolPlatilloBody,
    user: dict = Depends(get_current_user),
):
    """Propietario (invite_manage): editor ↔ solo_ver. No asigna propietario."""
    tipo_cuenta_id = await _resolve_tipo_cuenta_id(user["_token"], body.tipo_cuenta_id)
    row = await db(user["_token"]).update(
        "platillo_compartido",
        {"platillo_id": platillo_id, "usuario_invitado_id": usuario_id},
        {"tipo_cuenta_id": tipo_cuenta_id},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    return row


@router.delete("/platillo_compartido/{platillo_id}/usuario/{usuario_id}", status_code=204)
async def revocar_acceso_platillo(
    platillo_id: str, usuario_id: str, user: dict = Depends(get_current_user)
):
    await db(user["_token"]).delete(
        "platillo_compartido",
        {"platillo_id": platillo_id, "usuario_invitado_id": usuario_id},
    )
