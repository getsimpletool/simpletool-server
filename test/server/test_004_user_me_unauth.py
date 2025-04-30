import pytest
import httpx

@pytest.mark.asyncio
async def test_004_user_me_unauth(server_url):
    r = await httpx.AsyncClient().get(f"{server_url}/user/me")
    assert r.status_code == 401
    assert r.json() == {"detail": "Not authenticated"}
