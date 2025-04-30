import pytest
import httpx

@pytest.mark.asyncio
async def test_002_root(server_url):
    r = await httpx.AsyncClient().get(f"{server_url}/")
    assert r.status_code == 200
