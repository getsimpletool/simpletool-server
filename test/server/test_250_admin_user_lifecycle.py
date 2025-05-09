import pytest
import httpx
import json


@pytest.mark.asyncio
async def test_250_admin_user_lifecycle(server_url, admin_auth_token):
    """
    Test the full user lifecycle:
    1. Create a new user as admin
    2. Login as the new user
    3. Get user profile information
    4. Change the user's password
    5. Login with the new password
    6. Delete the user as admin
    """
    admin_headers = {"Authorization": f"Bearer {admin_auth_token}", "Content-Type": "application/json"}
    
    # Test user credentials
    test_username = "testuser"
    test_password = "testuser123"
    new_password = "UserTest123"
    
    async with httpx.AsyncClient() as client:
        # 1. Create a new user as admin
        user_data = {
            "username": test_username,
            "password": test_password,
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
        assert created_user["username"] == test_username, f"Expected username '{test_username}', got {created_user['username']}"
        assert created_user["admin"] is False, "User should not have admin privileges"
        assert created_user["disabled"] is False, "User should not be disabled"
        
        # 2. Login as the new user
        login_data = {
            "username": test_username,
            "password": test_password
        }
        
        resp = await client.post(
            f"{server_url}/user/login",
            json=login_data
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        token_data = resp.json()
        assert "access_token" in token_data, f"Expected 'access_token' in response, got {token_data}"
        assert token_data["token_type"] == "bearer", f"Expected token_type 'bearer', got {token_data['token_type']}"
        
        user_token = token_data["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}
        
        # 3. Get user profile information
        resp = await client.get(
            f"{server_url}/user/me",
            headers=user_headers
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        user_profile = resp.json()
        assert user_profile["username"] == test_username, f"Expected username '{test_username}', got {user_profile['username']}"
        assert user_profile["admin"] is False, "User should not have admin privileges"
        
        # 4. Change the user's password
        password_update = {
            "current_password": test_password,
            "new_password": new_password
        }
        
        resp = await client.put(
            f"{server_url}/user/password",
            headers=user_headers,
            json=password_update
        )
        
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}: {resp.text}"
        
        # 5. Login with the new password
        login_data = {
            "username": test_username,
            "password": new_password
        }
        
        resp = await client.post(
            f"{server_url}/user/login",
            json=login_data
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        token_data = resp.json()
        assert "access_token" in token_data, f"Expected 'access_token' in response, got {token_data}"
        
        # 6. Delete the user as admin
        resp = await client.delete(
            f"{server_url}/admin/user/{test_username}",
            headers=admin_headers
        )
        
        assert resp.status_code == 204, f"Expected 204, got {resp.status_code}: {resp.text}"
        
        # Verify the user is deleted by trying to login
        login_data = {
            "username": test_username,
            "password": new_password
        }
        
        resp = await client.post(
            f"{server_url}/user/login",
            json=login_data
        )
        
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
