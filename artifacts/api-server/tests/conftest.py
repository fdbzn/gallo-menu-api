"""Shared fixtures and helpers for Gallo API unit tests."""
import os

# Set env vars BEFORE any app imports, since Settings is a module-level singleton
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-key-for-unit-tests")

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient

TEST_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]


@pytest.fixture
def mock_db():
    """Return a MagicMock that behaves like a PostgREST client.

    Tests can override return values::

        mock_db.select.return_value = [{"id": "1"}]
    """
    client = MagicMock()
    client.select = AsyncMock(return_value=[])
    client.select_one = AsyncMock(return_value=None)
    client.insert = AsyncMock(return_value={})
    client.upsert = AsyncMock(return_value=None)
    client.update = AsyncMock(return_value=None)
    client.delete = AsyncMock(return_value=1)
    client.rpc = AsyncMock(return_value=None)
    return client


@pytest.fixture(scope="session")
def _app():
    """Import the FastAPI app once per session."""
    from main import app as fastapi_app
    return fastapi_app


@pytest.fixture
async def client(_app, mock_db):
    """Async HTTP client with ASGITransport + mocked PostgREST.

    Patches ``PostgREST`` class so ``db(token)`` returns our mock
    instead of creating real HTTP clients.
    """
    import app.database as db_mod

    with patch.object(db_mod, "PostgREST", return_value=mock_db):
        transport = ASGITransport(app=_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac


@pytest.fixture
def valid_user_claims():
    """Return a dict that simulates decoded Supabase JWT claims."""
    return {
        "sub": "550e8400-e29b-41d4-a716-446655440000",
        "email": "test@example.com",
        "aud": "authenticated",
        "role": "authenticated",
    }


@pytest.fixture
def auth_headers(valid_user_claims):
    """Build Authorization header dict with a fake valid token."""
    from jose import jwt
    token = jwt.encode(valid_user_claims, TEST_JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}
