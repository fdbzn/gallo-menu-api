"""Página pública de confirmación de cuenta."""


class TestCuentaConfirmada:
    async def test_returns_ok_html(self, client):
        resp = await client.get("/cuenta-confirmada")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        body = resp.text
        assert "Todo listo" in body
        assert "muchi://login" in body
        assert "Abrir la app" in body

    async def test_also_serves_api_prefix(self, client):
        resp = await client.get("/api/cuenta-confirmada")
        assert resp.status_code == 200
        assert "Todo listo" in resp.text

    async def test_shows_error_from_query(self, client):
        resp = await client.get(
            "/cuenta-confirmada",
            params={"error": "access_denied", "error_description": "Enlace inválido"},
        )
        assert resp.status_code == 200
        assert "No se pudo confirmar" in resp.text
        assert "Enlace inválido" in resp.text
