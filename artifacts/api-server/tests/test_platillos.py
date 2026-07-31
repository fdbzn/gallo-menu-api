"""Tests for Módulo 7 — Platillos e ingredientes del platillo."""
import pytest
from unittest.mock import patch, AsyncMock


class TestCatalogoTiposComida:
    async def test_returns_tipos(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [
            {"id": 1, "nombre": "desayuno"},
            {"id": 2, "nombre": "comida"},
            {"id": 3, "nombre": "cena"},
            {"id": 4, "nombre": "otro"},
        ]
        resp = await client.get("/cat_tipos_comida", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 4


class TestListPlatillos:
    async def test_returns_with_tipos_and_ingredientes(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [{
            "id": "p1", "nombre": "Tacos",
            "platillo_tipos": [{"tipo_comida_id": 2}],
            "platillo_ingredientes": [{"ingrediente_id": "i1", "cantidad": "2 tazas"}],
        }]
        resp = await client.get("/platillos", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()[0]["nombre"] == "Tacos"


class TestCreatePlatillo:
    async def test_creates_with_tipos(self, client, auth_headers, mock_db):
        mock_db.insert.side_effect = [
            {"id": "new", "nombre": "Pizza"},
            {"platillo_id": "new", "tipo_comida_id": 2},
            {"platillo_id": "new", "tipo_comida_id": 3},
        ]
        resp = await client.post(
            "/platillos", headers=auth_headers, json={"nombre": "Pizza", "tipos": [2, 3]}
        )
        assert resp.status_code == 201
        assert mock_db.insert.call_count == 3

    async def test_creates_without_tipos(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"id": "new", "nombre": "Solo"}
        resp = await client.post(
            "/platillos", headers=auth_headers, json={"nombre": "Solo", "tipos": []}
        )
        assert resp.status_code == 201


class TestUpdatePlatillo:
    async def test_updates_nombre_and_tipos(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"id": "p1", "nombre": "Nuevo"}
        mock_db.select.return_value = [{"id": "p1", "nombre": "Nuevo"}]
        mock_db.insert.return_value = {}
        mock_resp = AsyncMock()
        mock_resp.status_code = 204
        mock_resp.raise_for_status = AsyncMock()
        with patch("httpx.AsyncClient") as m:
            m.return_value.__aenter__.return_value.delete.return_value = mock_resp
            resp = await client.patch(
                "/platillos/p1", headers=auth_headers,
                json={"nombre": "Nuevo", "tipos": [1]}
            )
        assert resp.status_code == 200

    async def test_404_when_not_found(self, client, auth_headers, mock_db):
        mock_db.update.return_value = None
        resp = await client.patch(
            "/platillos/ghost", headers=auth_headers, json={"nombre": "No"}
        )
        assert resp.status_code == 404


class TestDeletePlatilloSimple:
    async def test_deletes_204(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 1
        resp = await client.delete("/platillos/p1", headers=auth_headers)
        assert resp.status_code == 204


class TestDeletePlatilloSelectivo:
    async def test_with_selected_ingredients_regla_7_6(self, client, auth_headers, mock_db):
        mock_db.rpc.return_value = None
        resp = await client.post(
            "/rpc/delete_platillo", headers=auth_headers,
            json={"platillo_id": "p1", "ingrediente_ids_a_borrar": ["i1", "i3"]}
        )
        assert resp.status_code == 204

    async def test_without_deleting_ingredients(self, client, auth_headers, mock_db):
        mock_db.rpc.return_value = None
        resp = await client.post(
            "/rpc/delete_platillo", headers=auth_headers,
            json={"platillo_id": "p1", "ingrediente_ids_a_borrar": []}
        )
        assert resp.status_code == 204


class TestPlatilloIngredientes:
    async def test_adds_ingrediente_regla_7_5_1(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"platillo_id": "p1", "ingrediente_id": "i1", "cantidad": "2 tazas"}
        resp = await client.post(
            "/platillo_ingredientes", headers=auth_headers,
            json={"platillo_id": "p1", "ingrediente_id": "i1", "cantidad": "2 tazas"}
        )
        assert resp.status_code == 201

    async def test_updates_cantidad_regla_7_5_3(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"platillo_id": "p1", "ingrediente_id": "i1", "cantidad": "500g"}
        resp = await client.patch(
            "/platillo_ingredientes?platillo_id=p1&ingrediente_id=i1",
            headers=auth_headers, json={"cantidad": "500g"}
        )
        assert resp.status_code == 200

    async def test_404_when_not_found(self, client, auth_headers, mock_db):
        mock_db.update.return_value = None
        resp = await client.patch(
            "/platillo_ingredientes?platillo_id=p1&ingrediente_id=missing",
            headers=auth_headers, json={"cantidad": "X"}
        )
        assert resp.status_code == 404

    async def test_removes_regla_7_5_2(self, client, auth_headers):
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.AsyncClient") as m:
            m.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_resp)
            resp = await client.delete(
                "/platillo_ingredientes?platillo_id=p1&ingrediente_id=i1",
                headers=auth_headers
            )
        assert resp.status_code == 204
