import pytest
import httpx
import json
import asyncio


@pytest.mark.asyncio
async def test_200_admin_mcpserver_lifecycle(server_url, admin_auth_token):
    """
    Test the full lifecycle of a MCP server:
    1. Create a new server via POST /admin/mcpserver
    2. Verify it appears in GET /admin/mcpservers
    3. Use a tool from the server via /tool/time/get_current_time
    """
    # 1. Create a new "time" server with specified configuration
    time_server_config = {
        "mcpServers": {
            "time": {
                "command": "uvx",
                "args": [
                    "mcp-server-time",
                    "--local-timezone=Europe/Warsaw"
                ],
                "env": {},
                "description": "time server",
                "disabled": False
            }
        }
    }

    headers = {"Authorization": f"Bearer {admin_auth_token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        # Add the server
        resp = await client.post(
            f"{server_url}/public/mcpserver",
            headers=headers,
            content=json.dumps(time_server_config)
        )

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("status") == "success", f"Expected 'success', got {data.get('status')}: {data}"

        # 2. Verify server appears in the list
        resp = await client.get(f"{server_url}/public/mcpservers", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert "mcpservers" in data, f"Expected 'mcpservers' key in response, got {data}"

        # Find the time server in the list
        time_server_found = False
        for server in data["mcpservers"]:
            if server.get("name") == "time":
                time_server_found = True
                break

        assert time_server_found, f"Time server not found in server list: {data['mcpservers']}"

        # 3. Wait a bit for the server to initialize and tools to be available
        await asyncio.sleep(2)

        # 4. Use a tool from the server - provide the required timezone parameter
        resp = await client.post(
            f"{server_url}/tool/time/get_current_time",
            headers=headers,
            json={"timezone": "Europe/Warsaw"}
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        # The response is in JSON-RPC format
        assert "jsonrpc" in data, f"Expected 'jsonrpc' in response, got {data}"
        assert "result" in data, f"Expected 'result' in response, got {data}"
        assert "content" in data["result"], f"Expected 'content' in result, got {data['result']}"

        # Extract the actual time data from the text field
        text_content = data["result"]["content"][0]["text"]
        time_data = json.loads(text_content)

        # Verify the timezone is correct
        assert "timezone" in time_data, f"Expected 'timezone' in time data, got {time_data}"
        assert time_data["timezone"] == "Europe/Warsaw", f"Expected timezone 'Europe/Warsaw', got {time_data['timezone']}"

        # Verify datetime is present
        assert "datetime" in time_data, f"Expected 'datetime' in time data, got {time_data}"
