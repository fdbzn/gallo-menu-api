"""Página pública de recuperación de contraseña."""
from unittest.mock import AsyncMock, MagicMock, patch


def _json_response(*, ok: bool, payload: dict, status_code: int = 200):
    resp = MagicMock()
    resp.is_success = ok
    resp.status_code = status_code
    resp.json.return_value = payload
    return resp


def _httpx_client(*, post_resp, put_resp=None):
    inner = AsyncMock()
    inner.post = AsyncMock(return_value=post_resp)
    inner.put = AsyncMock(return_value=put_resp or _json_response(ok=True, payload={}))
    ctx = AsyncMock()
    ctx.__aenter__.return_value = inner
    return ctx, inner


class TestResetPasswordGet:
    async def test_missing_token_shows_invalid(self, client):
        resp = await client.get("/auth/reset-password")
        assert resp.status_code == 200
        assert "Enlace inválido" in resp.text
        assert "moussi://login" in resp.text
        assert 'id="field-access-token"' in resp.text
        assert "window.location.hash" in resp.text

    async def test_root_trampolines_to_reset_password(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "location.replace" in resp.text
        assert "/api/auth/reset-password" in resp.text
        assert "/api/cuenta-confirmada" in resp.text

    async def test_also_serves_api_prefix(self, client):
        resp = await client.get(
            "/api/auth/reset-password",
            params={"token_hash": "abc", "type": "recovery"},
        )
        assert resp.status_code == 200
        assert "Nueva contraseña" in resp.text

    async def test_form_and_deep_link_when_token_present(self, client):
        resp = await client.get(
            "/auth/reset-password",
            params={"token_hash": "tok123", "type": "recovery"},
        )
        assert resp.status_code == 200
        body = resp.text
        assert "Nueva contraseña" in body
        assert 'name="token_hash"' in body
        assert "tok123" in body
        assert "moussi://reset-password" in body
        assert "token_hash=tok123" in body
        assert "Abrir en Moussi" in body

    async def test_code_only_skips_web_form(self, client):
        resp = await client.get(
            "/auth/reset-password",
            params={"code": "pkce-code"},
        )
        assert resp.status_code == 200
        assert 'name="password"' not in resp.text
        assert "Abrir en Moussi" in resp.text
        assert "code=pkce-code" in resp.text

    async def test_shows_error_from_query(self, client):
        resp = await client.get(
            "/auth/reset-password",
            params={"error": "access_denied", "error_description": "Enlace inválido"},
        )
        assert resp.status_code == 200
        assert "No se pudo restablecer" in resp.text
        assert "Enlace inválido" in resp.text


class TestResetPasswordPost:
    async def test_mismatch_keeps_form(self, client):
        resp = await client.post(
            "/auth/reset-password",
            data={
                "token_hash": "tok",
                "type": "recovery",
                "password": "nuevaclave1",
                "confirm_password": "nuevaclave2",
            },
        )
        assert resp.status_code == 200
        assert "Las contraseñas no coinciden" in resp.text
        assert 'name="password"' in resp.text

    async def test_short_password_keeps_form(self, client):
        resp = await client.post(
            "/auth/reset-password",
            data={
                "token_hash": "tok",
                "type": "recovery",
                "password": "short",
                "confirm_password": "short",
            },
        )
        assert resp.status_code == 200
        assert "al menos 8 caracteres" in resp.text

    async def test_invalid_hash_shows_expired(self, client):
        ctx, _inner = _httpx_client(
            post_resp=_json_response(
                ok=False, payload={"msg": "Token has expired or is invalid"}, status_code=401
            )
        )
        with patch("app.routers.reset_password.httpx.AsyncClient", return_value=ctx):
            resp = await client.post(
                "/auth/reset-password",
                data={
                    "token_hash": "bad",
                    "type": "recovery",
                    "password": "nuevaclave1",
                    "confirm_password": "nuevaclave1",
                },
            )
        assert resp.status_code == 200
        assert "Enlace expirado" in resp.text
        assert "Token has expired" in resp.text

    async def test_success_updates_password(self, client):
        ctx, inner = _httpx_client(
            post_resp=_json_response(ok=True, payload={"access_token": "access-1"}),
            put_resp=_json_response(ok=True, payload={}),
        )
        with patch("app.routers.reset_password.httpx.AsyncClient", return_value=ctx):
            resp = await client.post(
                "/auth/reset-password",
                data={
                    "token_hash": "good",
                    "type": "recovery",
                    "password": "nuevaclave1",
                    "confirm_password": "nuevaclave1",
                },
            )
        assert resp.status_code == 200
        assert "Contraseña actualizada" in resp.text
        assert "Abre Moussi" in resp.text
        inner.post.assert_awaited()
        inner.put.assert_awaited()
        put_kwargs = inner.put.await_args
        assert put_kwargs.kwargs["json"] == {"password": "nuevaclave1"}
        assert "Bearer access-1" in put_kwargs.kwargs["headers"]["Authorization"]

    async def test_access_token_skips_verify(self, client):
        ctx, inner = _httpx_client(
            post_resp=_json_response(ok=True, payload={"access_token": "should-not-use"}),
            put_resp=_json_response(ok=True, payload={}),
        )
        with patch("app.routers.reset_password.httpx.AsyncClient", return_value=ctx):
            resp = await client.post(
                "/auth/reset-password",
                data={
                    "access_token": "implicit-access",
                    "refresh_token": "implicit-refresh",
                    "type": "recovery",
                    "password": "nuevaclave1",
                    "confirm_password": "nuevaclave1",
                },
            )
        assert resp.status_code == 200
        assert "Contraseña actualizada" in resp.text
        inner.post.assert_not_awaited()
        inner.put.assert_awaited()
        put_kwargs = inner.put.await_args
        assert put_kwargs.kwargs["json"] == {"password": "nuevaclave1"}
        assert "Bearer implicit-access" in put_kwargs.kwargs["headers"]["Authorization"]
