import pytest
import httpx

# Description and numbering follow former pattern but pytest will auto-discover
@pytest.mark.asyncio
async def test_001_health(server_url):
    r = await httpx.AsyncClient().get(f"{server_url}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
