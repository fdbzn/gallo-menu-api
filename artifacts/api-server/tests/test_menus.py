"""Tests for Módulo 5 — Menús y compartición."""
import pytest
from unittest.mock import patch, AsyncMock


class TestListMenusByMesa:
    async def test_returns_menus(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [
            {"id": "menu1", "nombre": "Cena", "mesa_trabajo_id": "m1"}
        ]
        resp = await client.get("/menus?mesa_trabajo_id=m1", headers=auth_headers)
        assert resp.status_code == 200

    async def test_requires_mesa_trabajo_id(self, client, auth_headers):
        resp = await client.get("/menus", headers=auth_headers)
        assert resp.status_code == 422


class TestCreateMenu:
    async def test_creates_menu(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"id": "new", "mesa_trabajo_id": "m1", "nombre": "Menú"}
        resp = await client.post(
            "/menus", headers=auth_headers,
            json={"mesa_trabajo_id": "m1", "nombre": "Menú"}
        )
        assert resp.status_code == 201


class TestUpdateMenu:
    async def test_updates_name(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"id": "menu1", "nombre": "Nuevo"}
        resp = await client.patch(
            "/menus/menu1", headers=auth_headers, json={"nombre": "Nuevo"}
        )
        assert resp.status_code == 200

    async def test_returns_404(self, client, auth_headers, mock_db):
        mock_db.update.return_value = None
        resp = await client.patch(
            "/menus/ghost", headers=auth_headers, json={"nombre": "No"}
        )
        assert resp.status_code == 404


class TestDeleteMenu:
    async def test_deletes_menu(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 1
        resp = await client.delete("/menus/menu1", headers=auth_headers)
        assert resp.status_code == 204

    async def test_delete_returns_404_when_nothing_deleted(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 0
        resp = await client.delete("/menus/ghost", headers=auth_headers)
        assert resp.status_code == 404


class TestMenuPlatillos:
    async def test_adds_platillo(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"menu_id": "menu1", "platillo_id": "p1"}
        resp = await client.post(
            "/menu_platillos", headers=auth_headers,
            json={"menu_id": "menu1", "platillo_id": "p1"}
        )
        assert resp.status_code == 201

    async def test_removes_platillo(self, client, auth_headers):
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.content = b""
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.AsyncClient") as m:
            m.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_resp)
            resp = await client.delete(
                "/menu_platillos?menu_id=menu1&platillo_id=p1", headers=auth_headers
            )
        assert resp.status_code == 204


class TestCompartirMenu:
    async def test_shares_menu(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"menu_id": "menu1", "usuario_invitado_id": "u2", "estado": "pendiente"}
        resp = await client.post(
            "/menu_compartido", headers=auth_headers,
            json={"menu_id": "menu1", "usuario_invitado_id": "u2"}
        )
        assert resp.status_code == 201


class TestResponderInvitacionMenu:
    async def test_accepts(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"menu_id": "menu1", "estado": "aceptado"}
        resp = await client.patch(
            "/menu_compartido/menu1", headers=auth_headers, json={"estado": "aceptado"}
        )
        assert resp.status_code == 200

    async def test_denies_deletes_row_regla_5_6(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 1
        resp = await client.patch(
            "/menu_compartido/menu1", headers=auth_headers, json={"estado": "denegado"}
        )
        assert resp.status_code == 200
        mock_db.delete.assert_called_once()

    async def test_404_when_not_found(self, client, auth_headers, mock_db):
        mock_db.update.return_value = None
        resp = await client.patch(
            "/menu_compartido/menu1", headers=auth_headers, json={"estado": "aceptado"}
        )
        assert resp.status_code == 404


class TestRevocarAccesoMenu:
    async def test_revokes_access(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 1
        resp = await client.delete("/menu_compartido/menu1/usuario/u2", headers=auth_headers)
        assert resp.status_code == 204


class TestPendingMenuInvitations:
    async def test_returns_pending(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [
            {"menu_id": "menu1", "estado": "pendiente", "menus": {"nombre": "Compartido"}}
        ]
        resp = await client.get("/menu_compartido/pendientes", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
