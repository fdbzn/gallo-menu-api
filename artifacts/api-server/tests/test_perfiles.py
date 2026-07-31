"""Tests for Módulo 0 — Perfil y búsqueda de usuarios."""
import pytest


class TestGetMyProfile:
    async def test_returns_profile_when_found(self, client, auth_headers, mock_db):
        mock_db.select_one.return_value = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nombre": "Test User",
        }
        resp = await client.get("/perfiles/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Test User"

    async def test_returns_404_when_profile_not_found(self, client, auth_headers, mock_db):
        mock_db.select_one.return_value = None
        resp = await client.get("/perfiles/me", headers=auth_headers)
        assert resp.status_code == 404

    async def test_returns_401_without_auth(self, client):
        resp = await client.get("/perfiles/me")
        assert resp.status_code == 401


class TestUpdateMyProfile:
    async def test_updates_nombre(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "nombre": "Nuevo Nombre",
        }
        resp = await client.patch(
            "/perfiles/me", headers=auth_headers, json={"nombre": "Nuevo Nombre"}
        )
        assert resp.status_code == 200
        assert resp.json()["nombre"] == "Nuevo Nombre"

    async def test_returns_404_when_not_found(self, client, auth_headers, mock_db):
        mock_db.update.return_value = None
        resp = await client.patch(
            "/perfiles/me", headers=auth_headers, json={"nombre": "No"}
        )
        assert resp.status_code == 404


class TestSearchUsers:
    async def test_returns_users_matching_query(self, client, auth_headers, mock_db):
        mock_db.select.side_effect = [
            [{"id": "u2", "nombre": "Alice"}, {"id": "u3", "nombre": "Bob"}, {"id": "u4", "nombre": "Charlie"}],
            [],
        ]
        resp = await client.get("/perfiles/buscar?q=a", headers=auth_headers)
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 3
        for r in results:
            assert r["es_amigo"] is False

    async def test_orders_friends_first_regla_6_4(self, client, auth_headers, mock_db):
        """Regla 6.4 — amigos aparecen primero."""
        mock_db.select.side_effect = [
            [{"id": "u2", "nombre": "Zoe"}, {"id": "u3", "nombre": "Alice"}, {"id": "u4", "nombre": "Bob"}],
            [{"amigo_id": "u3"}],
        ]
        resp = await client.get("/perfiles/buscar?q=o", headers=auth_headers)
        assert resp.status_code == 200
        results = resp.json()
        assert results[0]["id"] == "u3"
        assert results[0]["es_amigo"] is True

    async def test_requires_query_param(self, client, auth_headers):
        resp = await client.get("/perfiles/buscar", headers=auth_headers)
        assert resp.status_code == 422

    async def test_excludes_current_user(self, client, auth_headers, mock_db):
        mock_db.select.side_effect = [[], []]
        resp = await client.get("/perfiles/buscar?q=me", headers=auth_headers)
        assert resp.status_code == 200
