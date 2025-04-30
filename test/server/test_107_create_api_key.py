import pytest
import httpx


@pytest.mark.asyncio
async def test_107_create_api_key(server_url, auth_token):
    """
    Test creating an API key for the current user (admin).
    """
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = await client.post(f"{server_url}/user/api-keys", headers=headers)
        assert resp.status_code == 200, f"API key creation failed: {resp.text}"
        api_key = resp.json().get("api_key")
        assert api_key, "No api_key returned in response"
        # Store for next test if needed
        with open("/tmp/test_api_key.txt", "w", encoding="utf-8") as f:
            f.write(api_key)
