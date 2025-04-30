import pytest
import httpx
import json
import os


@pytest.mark.asyncio
async def test_108_delete_api_key(server_url, auth_token):
    """
    Test deleting an API key for the current user (admin).
    """
    # Read the api_key generated in the previous test
    with open("/tmp/test_api_key.txt", "r", encoding="utf-8") as f:
        api_key = f.read().strip()

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
        resp = await client.request(
            "DELETE",
            f"{server_url}/user/api-keys",
            headers=headers,
            content=json.dumps({"api_key": api_key})
        )
        assert resp.status_code == 204, f"API key deletion failed: {resp.text}"
        # Delete the test api key file
        try:
            os.remove("/tmp/test_api_key.txt")
        except FileNotFoundError:
            pass
