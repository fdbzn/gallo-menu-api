"""Tests for Módulo 8 — Listas de compras."""
import pytest
from unittest.mock import patch, AsyncMock


class TestGetListaByMenu:
    async def test_returns_lista_with_items_regla_8_4(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [{
            "id": "l1", "menu_id": "menu1", "nombre": "Lista Semanal",
            "lista_compra_items": [{
                "id": "item1", "ingrediente_id": "i1", "comprado": False,
                "lista_compra_item_platillos": [{"platillo_id": "p1"}],
            }],
        }]
        resp = await client.get("/listas_compras?menu_id=menu1", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["lista_compra_items"]) == 1

    async def test_404_when_not_found(self, client, auth_headers, mock_db):
        mock_db.select.return_value = []
        resp = await client.get("/listas_compras?menu_id=ghost", headers=auth_headers)
        assert resp.status_code == 404


class TestRenameLista:
    async def test_renames_regla_8_3(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"id": "l1", "nombre": "Nuevo"}
        resp = await client.patch(
            "/listas_compras/l1", headers=auth_headers, json={"nombre": "Nuevo"}
        )
        assert resp.status_code == 200

    async def test_404(self, client, auth_headers, mock_db):
        mock_db.update.return_value = None
        resp = await client.patch(
            "/listas_compras/ghost", headers=auth_headers, json={"nombre": "No"}
        )
        assert resp.status_code == 404


class TestToggleComprado:
    async def test_toggles_true(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"id": "item1", "comprado": True}
        resp = await client.patch(
            "/lista_compra_items/item1/comprado", headers=auth_headers,
            json={"comprado": True}
        )
        assert resp.status_code == 200

    async def test_404(self, client, auth_headers, mock_db):
        mock_db.update.return_value = None
        resp = await client.patch(
            "/lista_compra_items/ghost/comprado", headers=auth_headers,
            json={"comprado": True}
        )
        assert resp.status_code == 404


class TestMoveToLugar:
    async def test_moves_to_lugar_regla_8_5(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"id": "item1", "lugar_compra_id": "walmart"}
        resp = await client.patch(
            "/lista_compra_items/item1/lugar", headers=auth_headers,
            json={"lugar_compra_id": "walmart"}
        )
        assert resp.status_code == 200

    async def test_moves_to_null_regla_8_7(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"id": "item1", "lugar_compra_id": None}
        resp = await client.patch(
            "/lista_compra_items/item1/lugar", headers=auth_headers,
            json={"lugar_compra_id": None}
        )
        assert resp.status_code == 200
        assert resp.json()["lugar_compra_id"] is None


class TestReorderItem:
    async def test_sets_order(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"id": "item1", "orden": 3}
        resp = await client.patch(
            "/lista_compra_items/item1/orden", headers=auth_headers,
            json={"orden": 3}
        )
        assert resp.status_code == 200


class TestAddItemManual:
    async def test_adds_suelto_regla_8_9(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"id": "new", "agregado_manualmente": True}
        resp = await client.post(
            "/lista_compra_items", headers=auth_headers,
            json={"lista_compra_id": "l1", "ingrediente_id": "i1", "agregado_manualmente": True}
        )
        assert resp.status_code == 201


class TestRemoveItemManual:
    async def test_removes(self, client, auth_headers):
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.AsyncClient") as m:
            m.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_resp)
            resp = await client.delete(
                "/lista_compra_items/item1", headers=auth_headers
            )
        assert resp.status_code == 204


class TestAssignItemPlatillo:
    async def test_assigns_to_existing_regla_8_12(self, client, auth_headers, mock_db):
        mock_db.rpc.return_value = None
        resp = await client.post(
            "/rpc/assign_lista_item_platillo", headers=auth_headers,
            json={"item_id": "item1", "platillo_id": "p1"}
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Asignado correctamente"

    async def test_shows_platillos_regla_8_11(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [{
            "id": "l1", "menu_id": "menu1", "nombre": "Lista",
            "lista_compra_items": [{
                "id": "item1", "ingrediente_id": "i1",
                "lista_compra_item_platillos": [{"platillo_id": "p1"}, {"platillo_id": "p2"}],
            }],
        }]
        resp = await client.get("/listas_compras?menu_id=menu1", headers=auth_headers)
        items = resp.json()["lista_compra_items"]
        assert len(items[0]["lista_compra_item_platillos"]) == 2


class TestAssignItemPlatilloNuevo:
    async def test_creates_platillo_and_assigns_regla_8_12(self, client, auth_headers, mock_db):
        mock_db.rpc.return_value = None
        resp = await client.post(
            "/rpc/assign_lista_item_platillo_nuevo", headers=auth_headers,
            json={"item_id": "item1", "nombre": "Nuevo", "tipos": ["comida"]}
        )
        assert resp.status_code == 201
        assert resp.json()["detail"] == "Platillo creado y asignado"
