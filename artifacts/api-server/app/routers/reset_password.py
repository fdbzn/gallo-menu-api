"""Landing pública de recuperación de contraseña (destino del correo de Supabase).

GET no consume el token. Soporta:
- ?token_hash= (plantilla custom)
- #access_token=…&type=recovery (flujo implícito default; el hash no llega al server)
- GET / trampolín: Site URL de Cloud Run suele ser la raíz, no /auth/reset-password.

POST verifica token_hash o usa access_token del hash y actualiza la contraseña.
"""
from __future__ import annotations

import html
import json
from typing import Optional
from urllib.parse import quote, urlencode

import httpx
from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse

from app.config import settings

router = APIRouter(tags=["auth-web"])

_MIN_PASSWORD_LEN = 8
_RESET_PATH = "/api/auth/reset-password"
_CONFIRM_PATH = "/api/cuenta-confirmada"


def _login_deep_link() -> str:
    return settings.app_deep_link.strip() or "moussi://login"


def _reset_deep_link(
    *,
    token_hash: Optional[str],
    type_: str,
    code: Optional[str],
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
) -> str:
    base = settings.app_password_reset_deep_link.strip() or "moussi://reset-password"
    params: dict[str, str] = {}
    if token_hash:
        params["token_hash"] = token_hash
    if type_:
        params["type"] = type_
    if code:
        params["code"] = code
    if access_token:
        params["access_token"] = access_token
    if refresh_token:
        params["refresh_token"] = refresh_token
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


def _hash_script() -> str:
    deep_link_js = json.dumps(
        settings.app_password_reset_deep_link.strip() or "moussi://reset-password"
    )
    return f"""
<script>
(function () {{
  var hash = new URLSearchParams((window.location.hash || '').replace(/^#/, ''));
  var err = hash.get('error_description') || hash.get('error');
  var access = hash.get('access_token');
  var refresh = hash.get('refresh_token');
  var type = hash.get('type') || 'recovery';
  var missing = document.getElementById('missing');
  var formWrap = document.getElementById('form-wrap');
  var fail = document.getElementById('fail');
  if (err) {{
    if (missing) missing.classList.add('hidden');
    if (formWrap) formWrap.classList.add('hidden');
    if (fail) {{
      fail.classList.remove('hidden');
      var msg = document.getElementById('fail-msg');
      if (msg) msg.textContent = err;
    }}
    return;
  }}
  if (!access) return;
  if (missing) missing.classList.add('hidden');
  if (formWrap) formWrap.classList.remove('hidden');
  var at = document.getElementById('field-access-token');
  if (at) at.value = access;
  var rt = document.getElementById('field-refresh-token');
  if (rt && refresh) rt.value = refresh;
  var typeField = document.querySelector('#form-wrap input[name="type"]');
  if (typeField) typeField.value = type;
  var open = document.getElementById('open-app');
  if (open) {{
    var q = new URLSearchParams();
    q.set('access_token', access);
    if (refresh) q.set('refresh_token', refresh);
    q.set('type', type);
    var base = {deep_link_js};
    var sep = base.indexOf('?') >= 0 ? '&' : '?';
    open.href = base + sep + q.toString();
  }}
}})();
</script>
"""


def _shell(*, title: str, inner: str) -> str:
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title} · Moussi</title>
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
    .hidden {{ display: none; }}
  </style>
</head>
<body>
  {inner}
  {_hash_script()}
</body>
</html>"""


def _form_inner(
    *,
    token_hash: Optional[str],
    type_: str,
    code: Optional[str],
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    error: Optional[str] = None,
) -> str:
    deep_link = html.escape(
        _reset_deep_link(
            token_hash=token_hash,
            type_=type_,
            code=code,
            access_token=access_token,
            refresh_token=refresh_token,
        ),
        quote=True,
    )
    err_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    token_hash_val = html.escape(token_hash or "", quote=True)
    type_val = html.escape(type_ or "recovery", quote=True)
    access_val = html.escape(access_token or "", quote=True)
    refresh_val = html.escape(refresh_token or "", quote=True)
    return f"""
    {err_html}
    <form method="post" action="{_RESET_PATH}">
      <input type="hidden" name="token_hash" value="{token_hash_val}" />
      <input id="field-access-token" type="hidden" name="access_token" value="{access_val}" />
      <input id="field-refresh-token" type="hidden" name="refresh_token" value="{refresh_val}" />
      <input type="hidden" name="type" value="{type_val}" />
      <label for="password">Nueva contraseña</label>
      <input id="password" name="password" type="password" minlength="{_MIN_PASSWORD_LEN}" required autocomplete="new-password" />
      <label for="confirm_password">Confirmar contraseña</label>
      <input id="confirm_password" name="confirm_password" type="password" minlength="{_MIN_PASSWORD_LEN}" required autocomplete="new-password" />
      <button class="btn" type="submit">Actualizar contraseña</button>
    </form>
    <a id="open-app" class="btn secondary" href="{deep_link}">Abrir en Moussi</a>"""


def _landing_page(
    *,
    token_hash: Optional[str],
    type_: str,
    code: Optional[str],
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    error: Optional[str] = None,
) -> str:
    has_server_token = bool(token_hash or access_token)
    code_only = bool(code) and not has_server_token
    missing_class = "hidden" if (has_server_token or code_only) else ""
    form_class = "" if (has_server_token or code_only) else "hidden"
    if code_only:
        form_html = f"""
      <p>Abre la app Moussi para continuar. Si el enlace no abre sola, pulsa el botón.</p>
      <a id="open-app" class="btn" href="{html.escape(_reset_deep_link(token_hash=None, type_=type_, code=code), quote=True)}">Abrir en Moussi</a>"""
    else:
        form_html = _form_inner(
            token_hash=token_hash,
            type_=type_,
            code=code,
            access_token=access_token,
            refresh_token=refresh_token,
            error=error,
        )

    login_link = html.escape(_login_deep_link(), quote=True)
    inner = f"""
  <main id="fail" class="card center hidden">
    <div class="badge err">!</div>
    <h1>No se pudo restablecer</h1>
    <p id="fail-msg">El enlace no es válido.</p>
    <a class="btn" href="{login_link}">Abrir la app</a>
  </main>
  <main id="missing" class="card center {missing_class}">
    <div class="badge err">!</div>
    <h1>Enlace inválido</h1>
    <p>Falta el token de recuperación. Si acabas de abrir el correo, espera un segundo o solicita un enlace nuevo desde la app.</p>
    <a class="btn" href="{login_link}">Abrir la app</a>
  </main>
  <main id="form-wrap" class="card {form_class}">
    <h1>Nueva contraseña</h1>
    <p>Elige una contraseña nueva para tu cuenta de Moussi. También puedes continuar en la app.</p>
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


def _trampoline_page() -> str:
    reset_path = json.dumps(_RESET_PATH)
    confirm_path = json.dumps(_CONFIRM_PATH)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Moussi</title>
</head>
<body>
  <p>Redirigiendo…</p>
  <script>
    (function () {{
      var hash = window.location.hash || '';
      var search = window.location.search || '';
      var params = new URLSearchParams(hash.replace(/^#/, ''));
      var type = params.get('type') || '';
      var dest = {reset_path};
      if (type === 'signup' || type === 'email') {{
        dest = {confirm_path};
      }}
      window.location.replace(dest + search + hash);
    }})();
  </script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def recovery_site_url_trampoline():
    """Site URL de Supabase es el origen de Cloud Run (`/`), no /auth/reset-password."""
    return HTMLResponse(_trampoline_page())


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
    return HTMLResponse(
        _landing_page(token_hash=hash_value, type_=type or "recovery", code=code)
    )


@router.post("/auth/reset-password", response_class=HTMLResponse)
@router.post("/api/auth/reset-password", response_class=HTMLResponse)
async def reset_password_post(
    token_hash: str = Form(default=""),
    access_token: str = Form(default=""),
    refresh_token: str = Form(default=""),
    type: str = Form(default="recovery"),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    token_hash = token_hash.strip()
    access_token = access_token.strip()
    refresh_token = refresh_token.strip() or None

    if password != confirm_password:
        return HTMLResponse(
            _landing_page(
                token_hash=token_hash or None,
                type_=type or "recovery",
                code=None,
                access_token=access_token or None,
                refresh_token=refresh_token,
                error="Las contraseñas no coinciden.",
            )
        )
    if len(password) < _MIN_PASSWORD_LEN:
        return HTMLResponse(
            _landing_page(
                token_hash=token_hash or None,
                type_=type or "recovery",
                code=None,
                access_token=access_token or None,
                refresh_token=refresh_token,
                error=f"La contraseña debe tener al menos {_MIN_PASSWORD_LEN} caracteres.",
            )
        )

    session_token = access_token or None
    if not session_token and token_hash:
        session_token, verify_error = await _verify_recovery(token_hash, type or "recovery")
        if not session_token:
            return HTMLResponse(
                _result_page(
                    ok=False,
                    title="Enlace expirado",
                    message=verify_error
                    or "El enlace expiró o ya se usó. Solicita uno nuevo desde la app.",
                )
            )
    if not session_token:
        return HTMLResponse(
            _result_page(
                ok=False,
                title="Enlace inválido",
                message="Falta el token de recuperación. Solicita un enlace nuevo desde la app.",
            )
        )

    update_error = await _update_password(session_token, password)
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
            message="Tu contraseña se cambió correctamente. Abre Moussi e inicia sesión.",
        )
    )
