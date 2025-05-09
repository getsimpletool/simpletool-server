import pytest
import httpx
import json
import asyncio


@pytest.mark.asyncio
async def test_202_admin_mcpserver_restart_all_servers(server_url, admin_auth_token):
    """
    Test restarting all MCP servers:
    1. Verify servers exist (created in previous tests)
    2. Use a tool from the time server to verify it works
    3. Restart all servers via POST /public/mcpservers/restart
    4. Verify the time server is still operational after restart
    """
    headers = {"Authorization": f"Bearer {admin_auth_token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        # 1. Verify servers exist from previous tests
        resp = await client.get(f"{server_url}/public/mcpservers", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert "mcpservers" in data, f"Expected 'mcpservers' key in response, got {data}"

        # Make sure we have at least one server
        assert len(data["mcpservers"]) > 0, "No servers found. Previous tests might have failed."

        # 2. Use a tool from the time server to verify it works initially
        resp = await client.post(
            f"{server_url}/tool/time/get_current_time",
            headers=headers,
            json={"timezone": "Europe/Warsaw"}
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        # 3. Restart all servers
        resp = await client.post(
            f"{server_url}/public/mcpservers/restart",
            headers=headers
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("status") == "success", f"Expected 'success', got {data.get('status')}: {data}"

        # The response should contain information about restarted servers
        assert "servers" in data, f"Expected 'servers' key in response, got {data}"

        # Wait for servers to restart
        await asyncio.sleep(3)

        # 4. Verify the time server is still operational after restart
        resp = await client.post(
            f"{server_url}/tool/time/get_current_time",
            headers=headers,
            json={"timezone": "Europe/Warsaw"}
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        # Verify the response format
        assert "jsonrpc" in data, f"Expected 'jsonrpc' in response, got {data}"
        assert "result" in data, f"Expected 'result' in response, got {data}"
        assert "content" in data["result"], f"Expected 'content' in result, got {data['result']}"

        # Extract the actual time data from the text field
        text_content = data["result"]["content"][0]["text"]
        time_data = json.loads(text_content)

        # Verify the timezone is correct
        assert "timezone" in time_data, f"Expected 'timezone' in time data, got {time_data}"
        assert time_data["timezone"] == "Europe/Warsaw", f"Expected timezone 'Europe/Warsaw', got {time_data['timezone']}"
