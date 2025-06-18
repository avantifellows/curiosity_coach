import httpx
import os
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file in the tests/ directory
load_dotenv()

# Fetch config from environment variables
BACKEND_API_URL = os.getenv("BACKEND_API_URL")
TEST_USER_PHONE_NUMBER = os.getenv("TEST_USER_PHONE_NUMBER")


@pytest.mark.skipif(not all([BACKEND_API_URL, TEST_USER_PHONE_NUMBER]), 
                    reason="BACKEND_API_URL or TEST_USER_PHONE_NUMBER not set in .env file")
def test_login(authenticated_user):
    """
    Tests that the authentication fixture works and returns the correct user data.
    """
    assert "user" in authenticated_user
    assert "access_token" in authenticated_user
    assert authenticated_user["user"]["phone_number"] == TEST_USER_PHONE_NUMBER
    print(f"Successfully logged in user {authenticated_user['user']['phone_number']}")


@pytest.mark.skipif(not all([BACKEND_API_URL, TEST_USER_PHONE_NUMBER]), 
                    reason="BACKEND_API_URL or TEST_USER_PHONE_NUMBER not set in .env file")
def test_list_conversations(client: httpx.Client):
    """
    Tests fetching the list of conversations for the authenticated user.
    """
    print("Fetching conversations for the authenticated user...")
    
    try:
        response = client.get("/api/conversations")
    except httpx.ConnectError as e:
        pytest.fail(f"Connection to backend failed at {BACKEND_API_URL}. Is the backend service running? Error: {e}", pytrace=False)

    # Assert that the request was successful
    assert response.status_code == 200, (
        f"Failed to get conversations. Status: {response.status_code}, "
        f"Response: {response.text}"
    )
    
    conversations = response.json()
    assert isinstance(conversations, list), "The conversations endpoint should return a list"
    
    print(f"Successfully retrieved {len(conversations)} conversations.")
    if conversations:
        assert "id" in conversations[0]
        assert "title" in conversations[0] 