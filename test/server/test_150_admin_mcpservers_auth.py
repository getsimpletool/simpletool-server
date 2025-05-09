import pytest
import httpx


@pytest.mark.asyncio
async def test_150_admin_mcpservers_auth(server_url, admin_auth_token):
    """
    Test MCP servers endpoints:
    1. GET /public/mcpservers - publicly accessible without authentication
    2. GET /user/mcpservers - requires authentication
    """
    # 1. Test public endpoint - should be accessible without authentication
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{server_url}/public/mcpservers")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert isinstance(data, dict), f"Expected a dict, got {type(data)}: {data}"
        assert "mcpservers" in data, f"Expected 'mcpservers' key in response, got {data}"
        assert isinstance(data["mcpservers"], list), f"'mcpservers' should be a list, got {type(data['mcpservers'])}: {data['mcpservers']}"

    # 2. Test user endpoint - without authentication
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{server_url}/user/mcpservers")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("detail") == "Not authenticated", f"Expected detail 'Not authenticated', got {data.get('detail')}"

    # 3. Test user endpoint - with admin token
    headers = {"Authorization": f"Bearer {admin_auth_token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{server_url}/user/mcpservers", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert isinstance(data, list), f"Expected a list, got {type(data)}: {data}"
