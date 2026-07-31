"""Módulo 5 — Menús y compartición."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import db
from app.deps import get_current_user

router = APIRouter(tags=["menus"])


class MenuBody(BaseModel):
    nombre: str


class CreateMenuBody(BaseModel):
    mesa_trabajo_id: str
    nombre: str


class MenuPlatilloBody(BaseModel):
    menu_id: str
    platillo_id: str


class CompartirMenuBody(BaseModel):
    menu_id: str
    usuario_invitado_id: str


class ResponderMenuBody(BaseModel):
    estado: str  # "aceptado" | "denegado"


# ── Menús ─────────────────────────────────────────────────────────────────────

@router.get("/menus")
async def list_menus_by_mesa(mesa_trabajo_id: str, user: dict = Depends(get_current_user)):
    return await db(user["_token"]).select(
        "menus",
        {
            "mesa_trabajo_id": f"eq.{mesa_trabajo_id}",
            "select": "*,menu_platillos(platillo_id),menu_compartido(*)",
            "order": "created_at.desc",
        },
    )


@router.post("/menus", status_code=201)
async def create_menu(body: CreateMenuBody, user: dict = Depends(get_current_user)):
    """Trigger crea lista de compras automáticamente (regla 8.1)."""
    client = db(user["_token"])
    row = await client.insert(
        "menus",
        {"mesa_trabajo_id": body.mesa_trabajo_id, "nombre": body.nombre},
    )
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
    row = await db(user["_token"]).update("menus", {"id": menu_id}, {"nombre": body.nombre})
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
    return await db(user["_token"]).insert(
        "menu_platillos", {"menu_id": body.menu_id, "platillo_id": body.platillo_id}
    )


@router.delete("/menu_platillos", status_code=204)
async def remove_platillo_from_menu(
    menu_id: str, platillo_id: str, user: dict = Depends(get_current_user)
):
    client = db(user["_token"])
    import httpx
    from app.config import settings
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {user['_token']}",
        "Prefer": "return=minimal",
    }
    async with httpx.AsyncClient(timeout=20) as http:
        resp = await http.delete(
            f"{settings.supabase_url}/rest/v1/menu_platillos",
            headers=headers,
            params={"menu_id": f"eq.{menu_id}", "platillo_id": f"eq.{platillo_id}"},
        )
    resp.raise_for_status()


# ── Compartición ──────────────────────────────────────────────────────────────

@router.post("/menu_compartido", status_code=201)
async def compartir_menu(body: CompartirMenuBody, user: dict = Depends(get_current_user)):
    """Estado inicial pendiente; trigger crea amistad automáticamente (regla 6.3)."""
    return await db(user["_token"]).insert(
        "menu_compartido",
        {"menu_id": body.menu_id, "usuario_invitado_id": body.usuario_invitado_id},
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


@router.delete("/menu_compartido/{menu_id}/usuario/{usuario_id}", status_code=204)
async def revocar_acceso_menu(
    menu_id: str, usuario_id: str, user: dict = Depends(get_current_user)
):
    await db(user["_token"]).delete(
        "menu_compartido", {"menu_id": menu_id, "usuario_invitado_id": usuario_id}
    )


@router.get("/menu_compartido/pendientes")
async def list_pending_menu_invitations(user: dict = Depends(get_current_user)):
    return await db(user["_token"]).select(
        "menu_compartido",
        {
            "usuario_invitado_id": f"eq.{user['sub']}",
            "estado": "eq.pendiente",
            "select": "*,menus(*)",
            "order": "created_at.desc",
        },
    )
