"""Tests for Módulo 4 — Mesas de trabajo."""
import pytest


class TestListMesas:
    async def test_returns_empty_list(self, client, auth_headers, mock_db):
        mock_db.select.return_value = []
        resp = await client.get("/mesas_trabajo", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_mesas_list(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [
            {"id": "m1", "nombre": "Casa"},
            {"id": "m2", "nombre": "Oficina"},
        ]
        resp = await client.get("/mesas_trabajo", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2
        args, _kwargs = mock_db.select.call_args
        assert "perfiles:creador_id" in args[1]["select"]

    async def test_unauthorized_without_token(self, client):
        resp = await client.get("/mesas_trabajo")
        assert resp.status_code == 401


class TestCreateMesa:
    async def test_creates_mesa_successfully(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {
            "id": "new-id", "nombre": "Nueva Mesa", "creador_id": "u1"
        }
        resp = await client.post(
            "/mesas_trabajo", headers=auth_headers, json={"nombre": "Nueva Mesa"}
        )
        assert resp.status_code == 201
        assert resp.json()["nombre"] == "Nueva Mesa"

    async def test_fails_validation_without_nombre(self, client, auth_headers):
        resp = await client.post("/mesas_trabajo", headers=auth_headers, json={})
        assert resp.status_code == 422


class TestUpdateMesa:
    async def test_updates_mesa_name(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"id": "m1", "nombre": "Actualizado"}
        resp = await client.patch(
            "/mesas_trabajo/m1", headers=auth_headers, json={"nombre": "Actualizado"}
        )
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Actualizado"

    async def test_returns_404_when_not_found(self, client, auth_headers, mock_db):
        mock_db.update.return_value = None
        resp = await client.patch(
            "/mesas_trabajo/ghost", headers=auth_headers, json={"nombre": "No"}
        )
        assert resp.status_code == 404


class TestDeleteMesa:
    async def test_deletes_returns_204(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 1
        resp = await client.delete("/mesas_trabajo/m1", headers=auth_headers)
        assert resp.status_code == 204

    async def test_silent_when_not_found(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 1
        resp = await client.delete("/mesas_trabajo/ghost", headers=auth_headers)
        assert resp.status_code == 204
