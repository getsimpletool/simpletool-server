import asyncio
import httpx
import pytest


@pytest.mark.asyncio
async def test_510_donald_mcpserver_env(server_url, admin_auth_token):
    """
    Test MCP server environment variables for non-admin user Donald:
    1. Login as Donald
    2. Add a calculator MCP server
    3. Add environment variables for the server
    4. Verify the environment variables are applied
    5. Update environment variables
    6. Delete environment variables
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

        # 2. Add calculator MCP server
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

        # 3. Set environment variables for the calculator server
        env_data = {
            "env": {
                "CALCULATOR_MODE": "scientific",
                "CALCULATOR_PRECISION": "10"
            }
        }

        resp = await client.put(
            f"{server_url}/user/mcpserver/calculator/env",
            headers=donald_headers,
            json=env_data
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        env_result = resp.json()
        assert env_result.get("CALCULATOR_MODE") == "scientific", f"Expected 'scientific', got {env_result.get('CALCULATOR_MODE')}"
        assert env_result.get("CALCULATOR_PRECISION") == "10", f"Expected '10', got {env_result.get('CALCULATOR_PRECISION')}"

        # 4. Get environment variables for the calculator server
        resp = await client.get(
            f"{server_url}/user/mcpserver/calculator",
            headers=donald_headers
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        env_result = resp.json()
        assert env_result.get("CALCULATOR_MODE") == "scientific", f"Expected 'scientific', got {env_result.get('CALCULATOR_MODE')}"
        assert env_result.get("CALCULATOR_PRECISION") == "10", f"Expected '10', got {env_result.get('CALCULATOR_PRECISION')}"

        # 5. Update a single environment variable
        resp = await client.put(
            f"{server_url}/user/mcpserver/calculator/env/CALCULATOR_MODE",
            headers=donald_headers,
            json={"value": "basic"}
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        user_data = resp.json()
        # The response should contain the user data with mcpServers.calculator.env
        assert "mcpServers" in user_data, f"Expected 'mcpServers' in response, got {user_data}"
        assert "calculator" in user_data["mcpServers"], f"Expected 'calculator' in mcpServers, got {user_data['mcpServers']}"
        assert "env" in user_data["mcpServers"]["calculator"], f"Expected 'env' in calculator config, got {user_data['mcpServers']['calculator']}"
        env_data = user_data["mcpServers"]["calculator"]["env"]
        assert env_data.get("CALCULATOR_MODE") == "basic", f"Expected 'basic', got {env_data.get('CALCULATOR_MODE')}"

        # Verify the update
        resp = await client.get(
            f"{server_url}/user/mcpserver/calculator",
            headers=donald_headers
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        user_data = resp.json()
        # The response should contain the user data with mcpServers.calculator.env
        assert "mcpServers" in user_data, f"Expected 'mcpServers' in response, got {user_data}"
        assert "calculator" in user_data["mcpServers"], f"Expected 'calculator' in mcpServers, got {user_data['mcpServers']}"
        assert "env" in user_data["mcpServers"]["calculator"], f"Expected 'env' in calculator config, got {user_data['mcpServers']['calculator']}"
        env_data = user_data["mcpServers"]["calculator"]["env"]
        assert env_data.get("CALCULATOR_MODE") == "basic", f"Expected 'basic', got {env_data.get('CALCULATOR_MODE')}"
        assert env_data.get("CALCULATOR_PRECISION") == "10", f"Expected '10', got {env_data.get('CALCULATOR_PRECISION')}"

        # 6. Delete a single environment variable
        resp = await client.delete(
            f"{server_url}/user/mcpserver/calculator/env/CALCULATOR_MODE",
            headers=donald_headers
        )

        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}: {resp.text}"

        # Verify the deletion
        resp = await client.get(
            f"{server_url}/user/mcpserver/calculator",
            headers=donald_headers
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        user_data = resp.json()
        # The response should contain the user data with mcpServers.calculator.env
        assert "mcpServers" in user_data, f"Expected 'mcpServers' in response, got {user_data}"
        assert "calculator" in user_data["mcpServers"], f"Expected 'calculator' in mcpServers, got {user_data['mcpServers']}"
        assert "env" in user_data["mcpServers"]["calculator"], f"Expected 'env' in calculator config, got {user_data['mcpServers']['calculator']}"
        env_data = user_data["mcpServers"]["calculator"]["env"]
        assert "CALCULATOR_MODE" not in env_data, f"Expected 'CALCULATOR_MODE' to be deleted, got {env_data}"
        assert env_data.get("CALCULATOR_PRECISION") == "10", f"Expected '10', got {env_data.get('CALCULATOR_PRECISION')}"

        # 7. Delete all environment variables
        resp = await client.delete(
            f"{server_url}/user/mcpserver/calculator/env",
            headers=donald_headers
        )

        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}: {resp.text}"

        # Verify all variables are deleted
        resp = await client.get(
            f"{server_url}/user/mcpserver/calculator",
            headers=donald_headers
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        user_data = resp.json()
        # The response should contain the user data with mcpServers.calculator.env
        assert "mcpServers" in user_data, f"Expected 'mcpServers' in response, got {user_data}"
        assert "calculator" in user_data["mcpServers"], f"Expected 'calculator' in mcpServers, got {user_data['mcpServers']}"
        # Check if env is empty or not present
        if "env" in user_data["mcpServers"]["calculator"]:
            assert user_data["mcpServers"]["calculator"]["env"] == {}, f"Expected empty env dict, got {user_data['mcpServers']['calculator']['env']}"

        print("Successfully tested environment variables for calculator server for user: " + donald_username)

        # 8. Clean up - stop the server
        resp = await client.delete(
            f"{server_url}/user/mcpserver/calculator-donald",
            headers=donald_headers
        )
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}: {resp.text}"
        print("Successfully stopped server: calculator-donald")
