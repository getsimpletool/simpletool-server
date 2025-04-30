import pytest
import httpx

@pytest.mark.asyncio
async def test_100_user_auth_and_me(server_url):
    # Login with admin credentials
    async with httpx.AsyncClient() as client:
        login_resp = await client.post(
            f"{server_url}/user/login", json={"username": "admin", "password": "admin"}
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        assert token is not None, "No access_token received"

        # Use token for authenticated request
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = await client.get(f"{server_url}/user/me", headers=headers)
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["username"] == "admin"
