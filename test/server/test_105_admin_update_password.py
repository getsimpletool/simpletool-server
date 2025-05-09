import pytest
import httpx
import asyncio


@pytest.mark.asyncio
async def test_105_admin_update_password(server_url, admin_auth_token):
    # Change password from admin to admin123
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {admin_auth_token}"}
        resp = await client.put(
            f"{server_url}/user/password",
            headers=headers,
            json={"current_password": "admin", "new_password": "admin123"}
        )
        assert resp.status_code == 204

        # Verify login with new credentials
        login_resp = await client.post(
            f"{server_url}/user/login", json={"username": "admin", "password": "admin123"}
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        new_token = login_resp.json().get("access_token")
        assert new_token, "No access_token received for new password"

        # Verify /user/me with new token
        me_resp = await client.get(
            f"{server_url}/user/me", headers={"Authorization": f"Bearer {new_token}"}
        )
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["username"] == "admin"

        # add sleep 2 sec
        await asyncio.sleep(2)

        # Rollback password to admin
        rollback_resp = await client.put(
            f"{server_url}/user/password",
            headers={"Authorization": f"Bearer {new_token}"},
            json={"current_password": "admin123", "new_password": "admin"}
        )
        assert rollback_resp.status_code == 204
        # Verify login with original admin credentials
        login_back = await client.post(
            f"{server_url}/user/login", json={"username": "admin", "password": "admin"}
        )
        assert login_back.status_code == 200
