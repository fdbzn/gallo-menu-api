"""Tests for Módulo 8 — Lugares de compra."""
import pytest


class TestListLugares:
    async def test_returns_empty(self, client, auth_headers, mock_db):
        mock_db.select.return_value = []
        resp = await client.get("/lugares_compra", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_list(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [
            {"id": "l1", "nombre": "Mercado"}, {"id": "l2", "nombre": "Walmart"}
        ]
        resp = await client.get("/lugares_compra", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestCreateLugar:
    async def test_creates(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"id": "new", "nombre": "Costco"}
        resp = await client.post(
            "/lugares_compra", headers=auth_headers, json={"nombre": "Costco"}
        )
        assert resp.status_code == 201

    async def test_fails_validation_without_nombre(self, client, auth_headers):
        resp = await client.post("/lugares_compra", headers=auth_headers, json={})
        assert resp.status_code == 422


class TestUpdateLugar:
    async def test_updates(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"id": "l1", "nombre": "Superama"}
        resp = await client.patch(
            "/lugares_compra/l1", headers=auth_headers, json={"nombre": "Superama"}
        )
        assert resp.status_code == 200

    async def test_404(self, client, auth_headers, mock_db):
        mock_db.update.return_value = None
        resp = await client.patch(
            "/lugares_compra/ghost", headers=auth_headers, json={"nombre": "No"}
        )
        assert resp.status_code == 404


class TestDeleteLugar:
    async def test_deletes_204(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 1
        resp = await client.delete("/lugares_compra/l1", headers=auth_headers)
        assert resp.status_code == 204
