"""Tests for Módulo 7 global — Ingredientes (inventario)."""
import pytest


class TestListIngredientes:
    async def test_returns_empty(self, client, auth_headers, mock_db):
        mock_db.select.return_value = []
        resp = await client.get("/ingredientes", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_list(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [
            {"id": "i1", "nombre": "Arroz"},
            {"id": "i2", "nombre": "Pollo"},
        ]
        resp = await client.get("/ingredientes", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestCreateIngrediente:
    async def test_creates_with_all_fields(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"id": "new", "nombre": "Sal", "categoria": "condimentos"}
        resp = await client.post(
            "/ingredientes", headers=auth_headers,
            json={"nombre": "Sal", "categoria": "condimentos", "stock": "1 kg"}
        )
        assert resp.status_code == 201

    async def test_creates_minimal(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"id": "min", "nombre": "Ajo"}
        resp = await client.post(
            "/ingredientes", headers=auth_headers, json={"nombre": "Ajo"}
        )
        assert resp.status_code == 201


class TestUpdateIngrediente:
    async def test_updates_partial(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"id": "i1", "nombre": "Sal Marina"}
        resp = await client.patch(
            "/ingredientes/i1", headers=auth_headers, json={"nombre": "Sal Marina"}
        )
        assert resp.status_code == 200

    async def test_noop_empty_body(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [{"id": "i1", "nombre": "Leche"}]
        resp = await client.patch("/ingredientes/i1", headers=auth_headers, json={})
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Leche"

    async def test_404_when_not_found(self, client, auth_headers, mock_db):
        mock_db.update.return_value = None
        resp = await client.patch(
            "/ingredientes/ghost", headers=auth_headers, json={"nombre": "No"}
        )
        assert resp.status_code == 404


class TestDeleteIngrediente:
    async def test_deletes_204(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 1
        resp = await client.delete("/ingredientes/i1", headers=auth_headers)
        assert resp.status_code == 204
