import pytest
import httpx


@pytest.mark.asyncio
async def test_120_admin_user_env_crud(server_url, admin_auth_token):
    """
    Test full CRUD cycle for user environment variables:
    - PUT /user/env (set env)
    - GET /user/env (read env)
    - PUT /user/env/{key} (update single key)
    - DELETE /user/env/{key} (delete single key)
    - DELETE /user/env (delete all env)
    """
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {admin_auth_token}"}

        # 1. PUT /user/env - set initial env
        env_data = {"env": {"FOO": "bar", "BAZ": "qux"}}
        resp = await client.put(f"{server_url}/user/env", headers=headers, json=env_data)
        assert resp.status_code == 200, f"Failed to set env: {resp.text}"
        assert resp.json()["FOO"] == "bar"
        assert resp.json()["BAZ"] == "qux"

        # 2. GET /user/env - read back
        resp = await client.get(f"{server_url}/user/env", headers=headers)
        assert resp.status_code == 200
        env = resp.json()
        assert env["FOO"] == "bar"
        assert env["BAZ"] == "qux"

        # 3. PUT /user/env/FOO - update single key
        resp = await client.put(f"{server_url}/user/env/FOO", headers=headers, json={"value": "newbar"})
        assert resp.status_code == 200, f"Failed to update env key: {resp.text}"
        assert resp.json()["FOO"] == "newbar"

        # 4. DELETE /user/env/FOO - delete single key
        resp = await client.delete(f"{server_url}/user/env/FOO", headers=headers)
        assert resp.status_code == 204, f"Failed to delete env key: {resp.text}"
        # Confirm deletion
        resp = await client.get(f"{server_url}/user/env", headers=headers)
        env = resp.json()
        assert "FOO" not in env
        assert "BAZ" in env

        # 5. DELETE /user/env - delete all
        resp = await client.delete(f"{server_url}/user/env", headers=headers)
        assert resp.status_code == 204, f"Failed to delete all env: {resp.text}"
        resp = await client.get(f"{server_url}/user/env", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {}  # should be empty
