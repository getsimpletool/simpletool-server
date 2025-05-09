import asyncio
import httpx
import pytest


@pytest.mark.asyncio
async def test_505_donald_mcpserver(server_url, admin_auth_token):
    """
    Test MCP server functionality for non-admin user Donald:
    1. Login as Donald
    2. Add two private MCP servers
    3. List private MCP servers
    4. Verify both servers are visible
    """
    # Donald user credentials
    donald_username = "donald"
    donald_password = "donaldduck"

    async with httpx.AsyncClient() as client:
        # 1. Login as Donald
        login_data = {
            "username": donald_username,
            "password": donald_password
        }

        resp = await client.post(
            f"{server_url}/user/login",
            json=login_data
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        token_data = resp.json()
        assert "access_token" in token_data, f"Expected 'access_token' in response, got {token_data}"

        donald_token = token_data["access_token"]
        donald_headers = {"Authorization": f"Bearer {donald_token}", "Content-Type": "application/json"}

        # 2. Add first MCP server (time server)
        time_server_config = {
            "mcpServers": {
                "time": {
                    "command": "uvx",
                    "args": [
                        "mcp-server-time",
                        "--local-timezone=Europe/Warsaw"
                    ]
                }
            }
        }

        resp = await client.post(
            f"{server_url}/user/mcpserver",
            headers=donald_headers,
            json=time_server_config
        )

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("status") == "success", f"Expected 'success', got {data.get('status')}: {data}"
        assert "time" in data.get("message", ""), f"Expected server name in message, got {data.get('message')}"

        # Wait a bit for the server to initialize
        await asyncio.sleep(2)

        # 3. Add second MCP server (calculator server)
        calculator_server_config = {
            "mcpServers": {
                "calculator": {
                    "command": "uvx",
                    "args": [
                        "mcp-server-calculator"
                    ]
                }
            }
        }

        resp = await client.post(
            f"{server_url}/user/mcpserver",
            headers=donald_headers,
            json=calculator_server_config
        )

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("status") == "success", f"Expected 'success', got {data.get('status')}: {data}"
        assert "calculator" in data.get("message", ""), f"Expected server name in message, got {data.get('message')}"

        # Wait a bit for the server to initialize
        await asyncio.sleep(2)

        # 4. List private MCP servers
        resp = await client.get(
            f"{server_url}/user/mcpservers",
            headers=donald_headers
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        servers = resp.json()

        # Verify both servers are in the list
        server_names = [server.get("name") for server in servers]
        assert "time-donald" in server_names, f"Expected 'time-donald' in server list, got {server_names}"
        assert "calculator-donald" in server_names, f"Expected 'calculator-donald' in server list, got {server_names}"

        # 5. Verify server details
        for server in servers:
            if server.get("name") == "time-donald":
                assert server.get("status") == "running", f"Expected status 'running', got {server.get('status')}"
            elif server.get("name") == "calculator-donald":
                assert server.get("status") == "running", f"Expected status 'running', got {server.get('status')}"

        print(f"Successfully created and verified two private MCP servers for user: {donald_username}")

        # 6. Clean up - stop the servers
        for server_name in ["time-donald", "calculator-donald"]:
            resp = await client.delete(
                f"{server_url}/user/mcpserver/{server_name}",
                headers=donald_headers
            )
            assert resp.status_code == 204, f"Expected 204, got {resp.status_code}: {resp.text}"
            print(f"Successfully stopped server: {server_name}")
