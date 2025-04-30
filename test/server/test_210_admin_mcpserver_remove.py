import pytest
import httpx
import json
import asyncio


@pytest.mark.asyncio
async def test_210_admin_mcpserver_remove(server_url, auth_token):
    """
    Test removing an MCP server:
    1. Verify the 'time' server exists (created in test_200)
    2. Remove the server via DELETE /admin/mcpserver/time
    3. Verify the server is no longer in the server list
    4. Verify the tool endpoint is no longer accessible
    """
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        # 1. Verify the 'time' server exists from previous test
        resp = await client.get(f"{server_url}/admin/mcpservers", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert "mcpservers" in data, f"Expected 'mcpservers' key in response, got {data}"
        
        # Find the time server in the list
        time_server_found = False
        for server in data["mcpservers"]:
            if server.get("name") == "time":
                time_server_found = True
                break
        
        assert time_server_found, f"Time server not found in server list. Previous tests might have failed."

        # 2. Remove the server
        resp = await client.delete(
            f"{server_url}/admin/mcpserver/time",
            headers=headers
        )
        
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}: {resp.text}"
        
        # 3. Verify the server is no longer in the list
        resp = await client.get(f"{server_url}/admin/mcpservers", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "mcpservers" in data, f"Expected 'mcpservers' key in response, got {data}"
        
        # Check that time server is no longer in the list
        for server in data["mcpservers"]:
            assert server.get("name") != "time", f"Time server still exists in server list after deletion"
        
        # 4. Verify the tool endpoint is no longer accessible
        resp = await client.post(
            f"{server_url}/tool/time/get_current_time",
            headers=headers,
            json={"timezone": "Europe/Warsaw"}
        )
        
        # Expect a 404 since the server and its tools should be gone
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
