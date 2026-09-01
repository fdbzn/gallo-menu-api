import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_privacy_policy_page(client: AsyncClient):
    for path in ["/privacidad", "/privacy", "/privacy-policy"]:
        resp = await client.get(path)
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Política de Privacidad" in resp.text
        assert "Moussi" in resp.text
