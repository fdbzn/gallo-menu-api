"""Tests for Módulo 9 — Encuestas."""
import pytest


class TestListEncuestas:
    async def test_returns_with_options_and_votes(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [{
            "id": "e1", "titulo": "¿Qué cenamos?", "estado": "activa",
            "encuesta_opciones": [{"id": "o1", "platillo_id": "p1"}],
            "encuesta_compartida": [],
            "encuesta_votos": [{"opcion_id": "o1", "usuario_id": "u2"}],
        }]
        resp = await client.get("/encuestas", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["titulo"] == "¿Qué cenamos?"

    async def test_returns_empty(self, client, auth_headers, mock_db):
        mock_db.select.return_value = []
        resp = await client.get("/encuestas", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateEncuesta:
    async def test_creates_regla_9_1(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"id": "new", "titulo": "¿Dónde?"}
        resp = await client.post(
            "/encuestas", headers=auth_headers, json={"titulo": "¿Dónde?"}
        )
        assert resp.status_code == 201

    async def test_fails_validation(self, client, auth_headers):
        resp = await client.post("/encuestas", headers=auth_headers, json={})
        assert resp.status_code == 422


class TestUpdateEncuesta:
    async def test_updates_titulo_regla_9_4(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"id": "e1", "titulo": "Nuevo"}
        resp = await client.patch(
            "/encuestas/e1", headers=auth_headers, json={"titulo": "Nuevo"}
        )
        assert resp.status_code == 200

    async def test_cierra_encuesta(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {
            "id": "e1", "estado": "cerrada", "fecha_cierre": "2026-07-30T00:00:00Z"
        }
        resp = await client.patch(
            "/encuestas/e1", headers=auth_headers,
            json={"estado": "cerrada", "fecha_cierre": "2026-07-30T00:00:00Z"}
        )
        assert resp.status_code == 200

    async def test_noop_empty(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [{"id": "e1", "titulo": "Igual"}]
        resp = await client.patch("/encuestas/e1", headers=auth_headers, json={})
        assert resp.status_code == 200

    async def test_404(self, client, auth_headers, mock_db):
        mock_db.update.return_value = None
        resp = await client.patch(
            "/encuestas/ghost", headers=auth_headers, json={"titulo": "No"}
        )
        assert resp.status_code == 404


class TestDeleteEncuesta:
    async def test_deletes_regla_9_4(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 1
        resp = await client.delete("/encuestas/e1", headers=auth_headers)
        assert resp.status_code == 204


class TestEncuestaOpciones:
    async def test_adds(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"id": "o-new", "encuesta_id": "e1", "platillo_id": "p1"}
        resp = await client.post(
            "/encuesta_opciones", headers=auth_headers,
            json={"encuesta_id": "e1", "platillo_id": "p1"}
        )
        assert resp.status_code == 201

    async def test_removes(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 1
        resp = await client.delete("/encuesta_opciones/o1", headers=auth_headers)
        assert resp.status_code == 204


class TestVotarEncuesta:
    async def test_vota(self, client, auth_headers, mock_db):
        mock_db.rpc.return_value = None
        resp = await client.post(
            "/rpc/votar_encuesta", headers=auth_headers,
            json={"encuesta_id": "e1", "opcion_id": "o1"}
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Voto registrado"


class TestGetVotos:
    async def test_returns_votos_regla_9_3(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [
            {"opcion_id": "o1", "usuario_id": "u2"},
            {"opcion_id": "o2", "usuario_id": "u3"},
        ]
        resp = await client.get("/encuesta_votos?encuesta_id=e1", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestCompartirEncuesta:
    async def test_shares_regla_6_3(self, client, auth_headers, mock_db):
        mock_db.insert.return_value = {"encuesta_id": "e1", "usuario_id": "u2", "estado": "pendiente"}
        resp = await client.post(
            "/encuesta_compartida", headers=auth_headers,
            json={"encuesta_id": "e1", "usuario_id": "u2"}
        )
        assert resp.status_code == 201


class TestResponderInvitacionEncuesta:
    async def test_accepts(self, client, auth_headers, mock_db):
        mock_db.update.return_value = {"encuesta_id": "e1", "estado": "aceptada"}
        resp = await client.patch(
            "/encuesta_compartida/e1", headers=auth_headers, json={"estado": "aceptada"}
        )
        assert resp.status_code == 200

    async def test_rejects_deletes_row(self, client, auth_headers, mock_db):
        mock_db.delete.return_value = 1
        resp = await client.patch(
            "/encuesta_compartida/e1", headers=auth_headers, json={"estado": "rechazada"}
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Invitación rechazada"


class TestPendingEncuestaInvitations:
    async def test_returns_pending(self, client, auth_headers, mock_db):
        mock_db.select.return_value = [{
            "encuesta_id": "e1", "estado": "pendiente",
            "encuestas": {"titulo": "Encuesta", "estado": "activa"},
        }]
        resp = await client.get("/encuesta_compartida/pendientes", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
