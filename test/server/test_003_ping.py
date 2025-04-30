import pytest
import httpx

@pytest.mark.asyncio
async def test_003_ping(server_url):
    r = await httpx.AsyncClient().get(f"{server_url}/ping")
    assert r.status_code == 200
    assert r.json() == {"response": "pong"}
