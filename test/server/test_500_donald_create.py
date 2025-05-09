import pytest
import httpx
import json


@pytest.mark.asyncio
async def test_500_donald_create(server_url, admin_auth_token):
    """
    Test creating a non-admin user named Donald:
    1. Create a new user 'donald' with password 'donaldduck' as admin
    2. Login as the new user
    3. Verify user profile information (non-admin)
    """
    admin_headers = {"Authorization": f"Bearer {admin_auth_token}", "Content-Type": "application/json"}

    # Donald user credentials
    donald_username = "donald"
    donald_password = "donaldduck"

    async with httpx.AsyncClient() as client:
        # 1. Create a new user (login as admin)
        user_data = {
            "username": donald_username,
            "password": donald_password,
            "admin": False,
            "disabled": False
        }

        resp = await client.post(
            f"{server_url}/admin/user",
            headers=admin_headers,
            json=user_data
        )

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        created_user = resp.json()
        assert created_user["username"] == donald_username, f"Expected username '{donald_username}', got {created_user['username']}"
        assert created_user["admin"] is False, "User should not have admin privileges"
        assert created_user["disabled"] is False, "User should not be disabled"

        # 2. Login as Donald
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
        assert token_data["token_type"] == "bearer", f"Expected token_type 'bearer', got {token_data['token_type']}"

        donald_token = token_data["access_token"]
        donald_headers = {"Authorization": f"Bearer {donald_token}", "Content-Type": "application/json"}

        # 3. Get user profile information
        resp = await client.get(
            f"{server_url}/user/me",
            headers=donald_headers
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        user_profile = resp.json()
        assert user_profile["username"] == donald_username, f"Expected username '{donald_username}', got {user_profile['username']}"
        assert user_profile["admin"] is False, "User should not have admin privileges"

        print(f"Successfully created and verified non-admin user: {donald_username}")
