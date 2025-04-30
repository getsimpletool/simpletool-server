import pytest
import httpx

@pytest.mark.asyncio
async def test_150_admin_mcpservers_auth(server_url, auth_token):
    """
    Test GET /admin/mcpservers:
    - Without authentication: returns 401 and detail 'Not authenticated'
    - With admin token: returns 200 and a dict with a 'mcpservers' key (list)
    """
    # 1. Without authentication
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{server_url}/admin/mcpservers")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("detail") == "Not authenticated", f"Expected detail 'Not authenticated', got {data.get('detail')}"

    # 2. With admin token (from auth_token fixture)
    headers = {"Authorization": f"Bearer {auth_token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{server_url}/admin/mcpservers", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert isinstance(data, dict), f"Expected a dict, got {type(data)}: {data}"
        assert "mcpservers" in data, f"Expected 'mcpservers' key in response, got {data}"
        assert isinstance(data["mcpservers"], list), f"'mcpservers' should be a list, got {type(data['mcpservers'])}: {data['mcpservers']}"
