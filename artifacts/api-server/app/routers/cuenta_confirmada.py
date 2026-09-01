"""Página pública de confirmación de cuenta (destino del correo de Supabase)."""
from __future__ import annotations

import html
from typing import Optional

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.config import settings

router = APIRouter(tags=["auth-web"])


def _deep_link() -> str:
    return settings.app_deep_link.strip() or "moussi://login"


async def _verify_token(token_hash: str, type_: str) -> tuple[bool, Optional[str]]:
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/verify"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {settings.supabase_anon_key}",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            url,
            headers=headers,
            json={"type": type_, "token_hash": token_hash},
        )
    if resp.is_success:
        return True, None
    try:
        detail = resp.json().get("msg") or resp.json().get("error_description")
    except Exception:
        detail = None
    return False, detail or "No se pudo confirmar el correo."


def _page(*, ok: bool, title: str, message: str) -> str:
    deep_link = html.escape(_deep_link(), quote=True)
    safe_title = html.escape(title)
    safe_message = html.escape(message)
    accent = "#9c27b0" if ok else "#B3261E"
    icon = "✓" if ok else "!"
    button = (
        f'<a class="btn" href="{deep_link}">Abrir la app</a>'
        if ok
        else f'<a class="btn" href="{deep_link}">Ir a Moussi</a>'
    )
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title} · Moussi</title>
  <style>
    :root {{
      --primary: #9c27b0;
      --on-surface: #1a1c1c;
      --muted: #4b4451;
      --bg: #f9f9f9;
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
      text-align: center;
      box-shadow: 0 8px 24px rgba(156, 39, 176, 0.08);
    }}
    .badge {{
      width: 64px;
      height: 64px;
      margin: 0 auto 16px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: {accent};
      color: #fff;
      font-size: 28px;
      font-weight: 700;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      color: #7B1FA2;
    }}
    p {{
      margin: 0 0 24px;
      color: var(--muted);
      line-height: 1.5;
    }}
    .btn {{
      display: inline-block;
      background: var(--primary);
      color: #fff;
      text-decoration: none;
      padding: 14px 28px;
      border-radius: 8px;
      font-weight: 600;
    }}
    .hidden {{ display: none; }}
  </style>
</head>
<body>
  <main class="card">
    <div id="ok" class="{'hidden' if not ok else ''}">
      <div class="badge">{icon if ok else '✓'}</div>
      <h1>¡Todo listo!</h1>
      <p>Tu cuenta de Moussi está confirmada. Abre la app para iniciar sesión.</p>
      {button if ok else ''}
    </div>
    <div id="fail" class="{'hidden' if ok else ''}">
      <div class="badge">!</div>
      <h1>{safe_title if not ok else 'No se pudo confirmar'}</h1>
      <p id="fail-msg">{safe_message if not ok else ''}</p>
      <a class="btn" href="{deep_link}">Abrir la app</a>
    </div>
  </main>
  <script>
    (function () {{
      var hash = new URLSearchParams(window.location.hash.replace(/^#/, ''));
      var err = hash.get('error_description') || hash.get('error');
      if (!err) return;
      var ok = document.getElementById('ok');
      var fail = document.getElementById('fail');
      var msg = document.getElementById('fail-msg');
      if (ok) ok.classList.add('hidden');
      if (fail) fail.classList.remove('hidden');
      if (msg) msg.textContent = err;
    }})();
  </script>
</body>
</html>"""


@router.get("/cuenta-confirmada", response_class=HTMLResponse)
@router.get("/api/cuenta-confirmada", response_class=HTMLResponse)
async def cuenta_confirmada(
    token_hash: Optional[str] = Query(default=None),
    token: Optional[str] = Query(default=None),
    type: str = Query(default="signup"),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
):
    if error or error_description:
        return HTMLResponse(
            _page(
                ok=False,
                title="No se pudo confirmar",
                message=error_description or error or "El enlace no es válido.",
            )
        )

    hash_value = token_hash or token
    if hash_value:
        verified, detail = await _verify_token(hash_value, type)
        if not verified:
            return HTMLResponse(
                _page(
                    ok=False,
                    title="No se pudo confirmar",
                    message=detail or "El enlace expiró o ya se usó.",
                )
            )

    return HTMLResponse(
        _page(
            ok=True,
            title="Cuenta confirmada",
            message="Tu cuenta de Moussi está confirmada.",
        )
    )
