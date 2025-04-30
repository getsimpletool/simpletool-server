import pytest
import httpx
import json
import asyncio


@pytest.mark.asyncio
async def test_201_admin_mcpserver_restart(server_url, auth_token):
    """
    Test restarting a specific MCP server:
    1. Verify the 'time' server exists (created in test_200)
    2. Use a tool from the server to verify it works
    3. Restart the server via POST /admin/mcpserver/{mcpserver_name}/restart
    4. Verify the server is still operational after restart
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

        assert time_server_found, f"Time server not found in server list. Test 200 might have failed or server was removed."

        # 2. Use a tool from the server to verify it works initially
        resp = await client.post(
            f"{server_url}/tool/time/get_current_time",
            headers=headers,
            json={"timezone": "Europe/Warsaw"}
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        # 3. Restart the server
        resp = await client.post(
            f"{server_url}/admin/mcpserver/time/restart",
            headers=headers
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("status") == "success", f"Expected 'success', got {data.get('status')}: {data}"
        assert data.get("server") == "time", f"Expected server 'time', got {data.get('server')}"

        # Wait for server to restart
        await asyncio.sleep(3)

        # 4. Verify the server is still operational after restart
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
