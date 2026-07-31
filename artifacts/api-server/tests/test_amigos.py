"""Tests for Módulo 6 — Amigos / Invitados a la mesa."""
import pytest


class TestListAmigos:
    async def test_returns_empty(self, client, auth_headers, mock_db):
        mock_db.select.return_value = []
        resp = await client.get("/amigos", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_friends_with_profiles(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [
            {"usuario_id": "u1", "amigo_id": "u2", "perfiles": {"id": "u2", "nombre": "Alice"}},
        ]
        resp = await client.get("/amigos", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()[0]["perfiles"]["nombre"] == "Alice"


class TestAgregarAmigo:
    async def test_adds_friend_via_rpc(self, client, auth_headers, mock_db):
        mock_db.rpc.return_value = None
        resp = await client.post(
            "/amigos/agregar", headers=auth_headers, json={"p_amigo_id": "u2"}
        )
        assert resp.status_code == 201
        assert resp.json()["detail"] == "Amistad creada"
        mock_db.rpc.assert_called_once_with("agregar_amigo", {"p_amigo_id": "u2"})


class TestCheckAmistad:
    async def test_returns_true(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [{"usuario_id": "u1", "amigo_id": "u2"}]
        resp = await client.get("/amigos/check/u2", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["es_amigo"] is True

    async def test_returns_false(self, client, auth_headers, mock_db):
        mock_db.select.return_value = []
        resp = await client.get("/amigos/check/u99", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["es_amigo"] is False
