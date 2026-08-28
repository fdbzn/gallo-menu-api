"""Landing pública de recuperación de contraseña (destino del correo de Supabase).

GET no consume el token: muestra el formulario y el deep link a la app.
POST verifica `token_hash` (tipo recovery) y actualiza la contraseña vía Auth REST.
"""
from __future__ import annotations

import html
from typing import Optional
from urllib.parse import quote, urlencode

import httpx
from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse

from app.config import settings

router = APIRouter(tags=["auth-web"])

_MIN_PASSWORD_LEN = 8


def _login_deep_link() -> str:
    return settings.app_deep_link.strip() or "muchi://login"


def _reset_deep_link(
    *,
    token_hash: Optional[str],
    type_: str,
    code: Optional[str],
) -> str:
    base = (settings.app_password_reset_deep_link.strip() or "muchi://reset-password")
    params: dict[str, str] = {}
    if token_hash:
        params["token_hash"] = token_hash
    if type_:
        params["type"] = type_
    if code:
        params["code"] = code
    if not params:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{urlencode(params, quote_via=quote)}"


def _auth_headers(bearer: str) -> dict[str, str]:
    return {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {bearer}",
    }


def _error_from_response(resp: httpx.Response) -> str:
    try:
        payload = resp.json()
        return (
            payload.get("msg")
            or payload.get("error_description")
            or payload.get("error")
            or payload.get("message")
            or "No se pudo completar la operación."
        )
    except Exception:
        return "No se pudo completar la operación."


async def _verify_recovery(token_hash: str, type_: str) -> tuple[Optional[str], Optional[str]]:
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/verify"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            url,
            headers=_auth_headers(settings.supabase_anon_key),
            json={"type": type_ or "recovery", "token_hash": token_hash},
        )
    if resp.is_success:
        token = resp.json().get("access_token")
        if not token:
            return None, "No se pudo validar el enlace."
        return token, None
    return None, _error_from_response(resp)


async def _update_password(access_token: str, password: str) -> Optional[str]:
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.put(
            url,
            headers=_auth_headers(access_token),
            json={"password": password},
        )
    if resp.is_success:
        return None
    return _error_from_response(resp)


def _shell(*, title: str, inner: str) -> str:
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title} · Muchi</title>
  <style>
    :root {{
      --primary: #9c27b0;
      --dark-primary: #7B1FA2;
      --on-surface: #1a1c1c;
      --muted: #4b4451;
      --bg: #f9f9f9;
      --error: #B3261E;
      --outline: #cdc3d3;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: Inter, system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--on-surface);
      padding: 24px;
    }}
    .card {{
      width: 100%;
      max-width: 420px;
      background: #fff;
      border-radius: 16px;
      padding: 32px 24px;
      box-shadow: 0 8px 24px rgba(156, 39, 176, 0.08);
    }}
    .card.center {{ text-align: center; }}
    .badge {{
      width: 64px;
      height: 64px;
      margin: 0 auto 16px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 28px;
      font-weight: 700;
    }}
    .badge.ok {{ background: var(--primary); }}
    .badge.err {{ background: var(--error); }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      color: var(--dark-primary);
    }}
    p {{
      margin: 0 0 20px;
      color: var(--muted);
      line-height: 1.5;
    }}
    label {{
      display: block;
      margin: 0 0 6px;
      font-size: 14px;
      font-weight: 600;
    }}
    input[type="password"] {{
      width: 100%;
      min-height: 48px;
      margin-bottom: 16px;
      padding: 12px 14px;
      border: 1px solid var(--outline);
      border-radius: 8px;
      font-size: 16px;
    }}
    .btn {{
      display: inline-block;
      width: 100%;
      background: var(--primary);
      color: #fff;
      text-decoration: none;
      text-align: center;
      border: 0;
      padding: 14px 28px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 16px;
      cursor: pointer;
    }}
    .btn.secondary {{
      background: transparent;
      color: var(--primary);
      margin-top: 12px;
    }}
    .error {{
      color: var(--error);
      font-size: 14px;
      margin: -8px 0 16px;
    }}
  </style>
</head>
<body>
  {inner}
</body>
</html>"""


def _form_page(
    *,
    token_hash: Optional[str],
    type_: str,
    code: Optional[str],
    error: Optional[str] = None,
) -> str:
    deep_link = html.escape(
        _reset_deep_link(token_hash=token_hash, type_=type_, code=code),
        quote=True,
    )
    err_html = (
        f'<p class="error">{html.escape(error)}</p>' if error else ""
    )
    form_html = ""
    if token_hash:
        form_html = f"""
      <form method="post" action="">
        <input type="hidden" name="token_hash" value="{html.escape(token_hash, quote=True)}" />
        <input type="hidden" name="type" value="{html.escape(type_, quote=True)}" />
        <label for="password">Nueva contraseña</label>
        <input id="password" name="password" type="password" minlength="{_MIN_PASSWORD_LEN}" required autocomplete="new-password" />
        <label for="confirm_password">Confirmar contraseña</label>
        <input id="confirm_password" name="confirm_password" type="password" minlength="{_MIN_PASSWORD_LEN}" required autocomplete="new-password" />
        <button class="btn" type="submit">Actualizar contraseña</button>
      </form>
      <a class="btn secondary" href="{deep_link}">Abrir en Muchi</a>"""
    else:
        form_html = f"""
      <p>Abre la app Muchi para continuar. Si el enlace no abre sola, pulsa el botón.</p>
      <a class="btn" href="{deep_link}">Abrir en Muchi</a>"""

    inner = f"""
  <main class="card">
    <h1>Nueva contraseña</h1>
    <p>Elige una contraseña nueva para tu cuenta de Muchi. También puedes continuar en la app.</p>
    {err_html}
    {form_html}
  </main>"""
    return _shell(title="Nueva contraseña", inner=inner)


def _result_page(*, ok: bool, title: str, message: str) -> str:
    deep_link = html.escape(_login_deep_link(), quote=True)
    badge = "ok" if ok else "err"
    icon = "✓" if ok else "!"
    inner = f"""
  <main class="card center">
    <div class="badge {badge}">{icon}</div>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(message)}</p>
    <a class="btn" href="{deep_link}">Abrir la app</a>
  </main>"""
    return _shell(title=title, inner=inner)


def _missing_link_page() -> str:
    return _result_page(
        ok=False,
        title="Enlace inválido",
        message="Falta el token de recuperación. Solicita un enlace nuevo desde la app.",
    )


@router.get("/auth/reset-password", response_class=HTMLResponse)
@router.get("/api/auth/reset-password", response_class=HTMLResponse)
async def reset_password_get(
    token_hash: Optional[str] = Query(default=None),
    token: Optional[str] = Query(default=None),
    type: str = Query(default="recovery"),
    code: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
):
    if error or error_description:
        return HTMLResponse(
            _result_page(
                ok=False,
                title="No se pudo restablecer",
                message=error_description or error or "El enlace no es válido.",
            )
        )

    hash_value = token_hash or token
    if not hash_value and not code:
        return HTMLResponse(_missing_link_page())

    return HTMLResponse(
        _form_page(token_hash=hash_value, type_=type or "recovery", code=code)
    )


@router.post("/auth/reset-password", response_class=HTMLResponse)
@router.post("/api/auth/reset-password", response_class=HTMLResponse)
async def reset_password_post(
    token_hash: str = Form(...),
    type: str = Form(default="recovery"),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    if password != confirm_password:
        return HTMLResponse(
            _form_page(
                token_hash=token_hash,
                type_=type or "recovery",
                code=None,
                error="Las contraseñas no coinciden.",
            )
        )
    if len(password) < _MIN_PASSWORD_LEN:
        return HTMLResponse(
            _form_page(
                token_hash=token_hash,
                type_=type or "recovery",
                code=None,
                error=f"La contraseña debe tener al menos {_MIN_PASSWORD_LEN} caracteres.",
            )
        )

    access_token, verify_error = await _verify_recovery(token_hash, type or "recovery")
    if not access_token:
        return HTMLResponse(
            _result_page(
                ok=False,
                title="Enlace expirado",
                message=verify_error or "El enlace expiró o ya se usó. Solicita uno nuevo desde la app.",
            )
        )

    update_error = await _update_password(access_token, password)
    if update_error:
        return HTMLResponse(
            _result_page(
                ok=False,
                title="No se pudo actualizar",
                message=update_error,
            )
        )

    return HTMLResponse(
        _result_page(
            ok=True,
            title="Contraseña actualizada",
            message="Tu contraseña se cambió correctamente. Abre Muchi e inicia sesión.",
        )
    )
