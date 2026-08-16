from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(tags=["menus"])


class MenuBody(BaseModel):
    nombre: str
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None


class CreateMenuBody(BaseModel):
    mesa_trabajo_id: str
    nombre: str
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None


class MenuPlatilloBody(BaseModel):
    menu_id: str
    platillo_id: str
    fecha: Optional[date] = None
    segmento_id: Optional[str] = None


class CompartirMenuBody(BaseModel):
    menu_id: str
    usuario_invitado_id: str
    tipo_cuenta_id: Optional[int] = None  # editor | solo_ver; default solo_ver


class ResponderMenuBody(BaseModel):
    estado: str  # "aceptado" | "denegado"


class CambiarRolMenuBody(BaseModel):
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
    return 3  # seed order: propietario=1, editor=2, solo_ver=3


# ── Menús ─────────────────────────────────────────────────────────────────────

@router.get("/menus")
async def list_menus_by_mesa(mesa_trabajo_id: str, user: dict = Depends(get_current_user)):
    return await db(user["_token"]).select(
        "menus",
        {
            "mesa_trabajo_id": f"eq.{mesa_trabajo_id}",
            "select": "*,menu_platillos(id,platillo_id,fecha,segmento_id,platillos(nombre)),menu_compartido(*,cat_tipos_cuenta(id,codigo,nombre))",
            "order": "created_at.desc",
        },
    )


@router.post("/menus", status_code=201)
async def create_menu(body: CreateMenuBody, user: dict = Depends(get_current_user)):
    """Trigger crea lista de compras automáticamente (regla 8.1)."""
    client = db(user["_token"])
    data = {"mesa_trabajo_id": body.mesa_trabajo_id, "nombre": body.nombre}
    if body.fecha_inicio is not None:
        data["fecha_inicio"] = body.fecha_inicio.isoformat()
    if body.fecha_fin is not None:
        data["fecha_fin"] = body.fecha_fin.isoformat()

    row = await client.insert("menus", data)
    if row.get("id"):
        return row
    rows = await client.select(
        "menus",
        {
            "mesa_trabajo_id": f"eq.{body.mesa_trabajo_id}",
            "nombre": f"eq.{body.nombre}",
            "order": "created_at.desc",
            "limit": "1",
        },
    )
    if rows:
        return rows[0]
    raise HTTPException(
        status_code=403,
        detail="No tienes permiso para crear menús en esta mesa (solo el creador de la mesa).",
    )


@router.patch("/menus/{menu_id}")
async def update_menu(menu_id: str, body: MenuBody, user: dict = Depends(get_current_user)):
    data = {"nombre": body.nombre}
    if body.fecha_inicio is not None:
        data["fecha_inicio"] = body.fecha_inicio.isoformat()
    if body.fecha_fin is not None:
        data["fecha_fin"] = body.fecha_fin.isoformat()

    row = await db(user["_token"]).update("menus", {"id": menu_id}, data)
    if not row:
        raise HTTPException(status_code=404, detail="Menú no encontrado o sin permiso")
    return row


@router.delete("/menus/{menu_id}", status_code=204)
async def delete_menu(menu_id: str, user: dict = Depends(get_current_user)):
    await db(user["_token"]).delete("menus", {"id": menu_id})


# ── Platillos del menú ────────────────────────────────────────────────────────

@router.post("/menu_platillos", status_code=201)
async def add_platillo_to_menu(body: MenuPlatilloBody, user: dict = Depends(get_current_user)):
    """Trigger sincroniza lista de compras automáticamente."""
    data = {"menu_id": body.menu_id, "platillo_id": body.platillo_id}
    if body.fecha is not None:
        data["fecha"] = body.fecha.isoformat()
    if body.segmento_id is not None:
        data["segmento_id"] = body.segmento_id
    return await db(user["_token"]).insert("menu_platillos", data)


@router.delete("/menu_platillos", status_code=204)
async def remove_platillo_from_menu(
    menu_id: str, platillo_id: str, user: dict = Depends(get_current_user), fecha: Optional[date] = None, segmento_id: Optional[str] = None
):
    client = db(user["_token"])
    import httpx
    from app.config import settings
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {user['_token']}",
        "Prefer": "return=minimal",
    }
    params = {"menu_id": f"eq.{menu_id}", "platillo_id": f"eq.{platillo_id}"}
    if fecha is not None:
        params["fecha"] = f"eq.{fecha.isoformat()}"
    else:
        params["fecha"] = "is.null"
    if segmento_id is not None:
        params["segmento_id"] = f"eq.{segmento_id}"
    else:
        params["segmento_id"] = "is.null"

    async with httpx.AsyncClient(timeout=20) as http:
        resp = await http.delete(
            f"{settings.supabase_url}/rest/v1/menu_platillos",
            headers=headers,
            params=params,
        )
    resp.raise_for_status()


# ── Compartición ──────────────────────────────────────────────────────────────

@router.post("/menu_compartido", status_code=201)
async def compartir_menu(body: CompartirMenuBody, user: dict = Depends(get_current_user)):
    """Estado inicial pendiente; trigger crea amistad automáticamente (regla 6.3)."""
    tipo_cuenta_id = await _resolve_tipo_cuenta_id(user["_token"], body.tipo_cuenta_id)
    return await db(user["_token"]).insert(
        "menu_compartido",
        {
            "menu_id": body.menu_id,
            "usuario_invitado_id": body.usuario_invitado_id,
            "tipo_cuenta_id": tipo_cuenta_id,
        },
    )


@router.patch("/menu_compartido/{menu_id}")
async def responder_invitacion_menu(
    menu_id: str, body: ResponderMenuBody, user: dict = Depends(get_current_user)
):
    if body.estado == "denegado":
        await db(user["_token"]).delete(
            "menu_compartido", {"menu_id": menu_id, "usuario_invitado_id": user["sub"]}
        )
        return {"detail": "Invitación rechazada"}
    row = await db(user["_token"]).update(
        "menu_compartido",
        {"menu_id": menu_id, "usuario_invitado_id": user["sub"]},
        {"estado": body.estado},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    return row


@router.patch("/menu_compartido/{menu_id}/usuario/{usuario_id}/rol")
async def cambiar_rol_menu(
    menu_id: str,
    usuario_id: str,
    body: CambiarRolMenuBody,
    user: dict = Depends(get_current_user),
):
    """Propietario (invite_manage): editor ↔ solo_ver. No asigna propietario."""
    tipo_cuenta_id = await _resolve_tipo_cuenta_id(user["_token"], body.tipo_cuenta_id)
    row = await db(user["_token"]).update(
        "menu_compartido",
        {"menu_id": menu_id, "usuario_invitado_id": usuario_id},
        {"tipo_cuenta_id": tipo_cuenta_id},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    return row


@router.delete("/menu_compartido/{menu_id}/usuario/{usuario_id}", status_code=204)
async def revocar_acceso_menu(
    menu_id: str, usuario_id: str, user: dict = Depends(get_current_user)
):
    await db(user["_token"]).delete(
        "menu_compartido", {"menu_id": menu_id, "usuario_invitado_id": usuario_id}
    )


@router.get("/menu_compartido/pendientes")
async def list_pending_menu_invitations(user: dict = Depends(get_current_user)):
    # SECURITY DEFINER RPC: includes menu/mesa/sharer preview while still pendiente
    return await db(user["_token"]).rpc("list_pending_menu_invitations", {})

