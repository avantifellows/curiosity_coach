import httpx
import os
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file in the tests/ directory
load_dotenv()

# Fetch config from environment variables
BACKEND_API_URL = os.getenv("BACKEND_API_URL")
TEST_USER_PHONE_NUMBER = os.getenv("TEST_USER_PHONE_NUMBER")


@pytest.fixture(scope="session")
def authenticated_user():
    """
    Logs in the test user and yields the user details and access token.
    This fixture has a 'session' scope, so it runs only once.
    """
    if not all([BACKEND_API_URL, TEST_USER_PHONE_NUMBER]):
        pytest.fail("BACKEND_API_URL or TEST_USER_PHONE_NUMBER not set in .env file", pytrace=False)

    with httpx.Client(base_url=BACKEND_API_URL) as client:
        login_payload = {"phone_number": TEST_USER_PHONE_NUMBER}
        try:
            response = client.post("/api/auth/login", json=login_payload, timeout=10)
        except httpx.ConnectError as e:
            pytest.fail(f"Connection to backend failed at {BACKEND_API_URL}. Is the backend service running? Error: {e}", pytrace=False)

        if response.status_code != 200:
            pytest.fail(f"Failed to login for tests. Status: {response.status_code}, Response: {response.text}", pytrace=False)

        response_json = response.json()
        user = response_json.get("user")
        if not user or "id" not in user:
            pytest.fail("User ID not found in login response.", pytrace=False)

        user_id = user["id"]
        access_token = str(user_id)
        
        yield {"user": user, "access_token": access_token}


@pytest.fixture()
def client(authenticated_user):
    """
    Provides an httpx client with the authentication header already set.
    """
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    with httpx.Client(base_url=BACKEND_API_URL, headers=headers) as client_instance:
        yield client_instance

# You can add other fixtures here if needed for your tests.