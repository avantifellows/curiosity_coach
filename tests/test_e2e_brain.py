import httpx
import pytest
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BACKEND_API_URL = os.getenv("BACKEND_API_URL")
BRAIN_API_URL = os.getenv("BRAIN_API_URL")

# Pytest markers
skip_if_no_backend = pytest.mark.skipif(not BACKEND_API_URL,
                                        reason="BACKEND_API_URL not set in .env file")
skip_if_no_brain = pytest.mark.skipif(not BRAIN_API_URL,
                                      reason="BRAIN_API_URL not set in .env file")

@pytest.fixture(scope="module")
def brain_client():
    """A client for making requests to the Brain service."""
    with httpx.Client(base_url=BRAIN_API_URL) as client:
        yield client

@skip_if_no_backend
@skip_if_no_brain
def test_brain_query_and_backend_callback(client: httpx.Client, brain_client: httpx.Client, authenticated_user):
    """
    Tests the full E2E flow:
    1. Create a conversation and message in the backend.
    2. Call the Brain's /query endpoint with the message details.
    3. Verify the Brain's immediate response.
    4. Poll the backend to verify the Brain's callback was successful and the AI message was stored.
    """
    # 1. Setup: Create a conversation and a user message in the backend
    print("\n--- E2E Brain Test: Setting up conversation and message in backend ---")
    conv_payload = {"title": "Brain E2E Test Conversation"}
    conv_response = client.post("/api/conversations", json=conv_payload)
    assert conv_response.status_code == 201
    conv_data = conv_response.json()
    conversation_id = conv_data["id"]

    msg_payload = {"content": "What is the powerhouse of the cell?"}
    msg_response = client.post(f"/api/conversations/{conversation_id}/messages", json=msg_payload)
    assert msg_response.status_code == 200
    msg_data = msg_response.json()["message"]
    user_message_id = msg_data["id"]
    
    print(f"Successfully created conversation {conversation_id} and message {user_message_id}")

    # 2. Call Brain's /query endpoint
    print(f"\n--- E2E Brain Test: Calling Brain /query endpoint ---")
    brain_query_payload = {
        "user_id": str(authenticated_user["user"]["id"]),
        "message_id": str(user_message_id),
        "purpose": "chat",
        "conversation_id": str(conversation_id),
        "message_content": msg_data["content"],
        "timestamp": time.time(),
        "is_follow_up_response": False
    }
    
    try:
        brain_response = brain_client.post("/query", json=brain_query_payload, timeout=30.0)
    except httpx.ConnectError as e:
        pytest.fail(f"Connection to Brain service failed at {BRAIN_API_URL}. Is it running? Error: {e}", pytrace=False)

    # 3. Verify Brain's immediate response
    assert brain_response.status_code == 200, f"Brain /query failed: {brain_response.text}"
    brain_response_data = brain_response.json()
    assert "final_response" in brain_response_data
    # A simple assertion, since the actual response can vary.
    # We mainly care that it processed and returned something.
    assert isinstance(brain_response_data["final_response"], str) 
    print("Successfully received immediate response from Brain.")

    # 4. Poll backend to verify callback
    print(f"\n--- E2E Brain Test: Polling backend for AI response from callback ---")
    ai_response_data = None
    for i in range(15): # Poll for ~15 seconds
        print(f"Polling attempt {i+1}...")
        poll_response = client.get(f"/api/messages/{user_message_id}/response")
        if poll_response.status_code == 200 and poll_response.text:
            try:
                ai_response_data = poll_response.json()
                if ai_response_data: # Make sure it's not an empty 200 response
                    break
            except ValueError:
                pass # Ignore JSON decode errors for empty responses
        time.sleep(1)
        
    assert ai_response_data is not None, "AI response was not found on backend after polling."
    assert ai_response_data["is_user"] is False
    # The immediate response from the brain's /query can be an intermediate step result (e.g., intent analysis).
    # The final response is what's sent in the callback. We verify that the final response stored in the
    # backend is a valid, non-empty string.
    assert isinstance(ai_response_data["content"], str)
    assert len(ai_response_data["content"]) > 0
    print(f"Successfully verified Brain callback and found AI message {ai_response_data['id']} on backend.")

    # Teardown: delete the conversation
    print(f"\n--- E2E Brain Test: Cleaning up conversation {conversation_id} ---")
    client.delete(f"/api/conversations/{conversation_id}")

@skip_if_no_brain
def test_brain_config_flow(brain_client: httpx.Client):
    """
    Tests setting and getting the FlowConfig on the Brain service.
    """
    # 1. Define a custom config
    print("\n--- Brain Config Test: Defining custom flow config ---")
    custom_config = {
        "use_simplified_mode": False,
        "steps": [
            {
                "name": "Intent Recognition",
                "enabled": False,
                "use_conversation_history": False,
                "is_use_conversation_history_valid": True, # Field is required
                "is_allowed_to_change_enabled": True      # Field is required
            },
            {
                "name": "Knowledge Retrieval",
                "enabled": True,
                "use_conversation_history": True,
                "is_use_conversation_history_valid": True,
                "is_allowed_to_change_enabled": True      # Field is required
            }
        ]
    }

    # 2. Set the custom config
    print("--- Brain Config Test: Setting custom config via /set-config ---")
    try:
        set_response = brain_client.post("/set-config", json=custom_config)
    except httpx.ConnectError as e:
        pytest.fail(f"Connection to Brain service failed at {BRAIN_API_URL}. Is it running? Error: {e}", pytrace=False)

    assert set_response.status_code == 200, f"Failed to set config: {set_response.text}"
    assert set_response.json()["message"] == "Configuration updated successfully."
    print("Successfully set custom config.")

    # Add a small delay for S3 to become consistent
    time.sleep(2)

    # 3. Get the config and verify it
    print("--- Brain Config Test: Getting config via /get-config ---")
    get_response = brain_client.get("/get-config")
    assert get_response.status_code == 200
    config_data = get_response.json()
    
    assert "schema" in config_data
    assert "current_values" in config_data
    
    retrieved_config = config_data["current_values"]
    # Compare the 'steps' part, as other defaults might be present
    assert retrieved_config.get("steps") == custom_config["steps"]
    print("Successfully verified the custom config was saved and retrieved.") 