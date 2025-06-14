import httpx
import pytest
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BACKEND_API_URL = os.getenv("BACKEND_API_URL")

# Pytest marker for skipping tests if the backend URL is not set
skip_if_no_backend = pytest.mark.skipif(not BACKEND_API_URL,
                                        reason="BACKEND_API_URL not set in .env file")

@pytest.fixture(scope="function")
def test_conversation(client: httpx.Client, authenticated_user):
    """
    Fixture to create a conversation for message tests.
    It will be created once for the module and cleaned up afterwards.
    """
    user_id = authenticated_user["user"]["id"]
    payload = {"user_id": user_id, "title": "Message Test Conversation"}
    
    response = client.post("/api/conversations", json=payload)
    assert response.status_code == 201
    conversation_data = response.json()
    
    yield conversation_data
    
    # Teardown: delete the conversation
    conversation_id = conversation_data["id"]
    delete_response = client.delete(f"/api/conversations/{conversation_id}")
    assert delete_response.status_code in [200, 204, 404]


@skip_if_no_backend
def test_create_and_list_messages(client: httpx.Client, test_conversation):
    """
    Tests creating a new message and then listing messages in a conversation.
    """
    conversation_id = test_conversation["id"]
    
    # Part 1: Create a message
    message_content = "Hello, this is a test message."
    message_payload = {
        "conversation_id": conversation_id,
        "content": message_content,
        "is_user": True
    }
    
    print(f"Creating message in conversation {conversation_id}...")
    create_response = client.post(f"/api/conversations/{conversation_id}/messages", json=message_payload)
    
    assert create_response.status_code == 200, f"Failed to create message: {create_response.text}"
    
    response_json = create_response.json()
    assert "message" in response_json
    message_data = response_json["message"]

    assert "id" in message_data
    assert message_data["content"] == message_content
    assert message_data["is_user"] is True
    print(f"Successfully created message with ID: {message_data['id']}")

    # Part 2: List messages in the conversation
    print(f"Listing messages for conversation {conversation_id}...")
    list_response = client.get(f"/api/conversations/{conversation_id}/messages")
    
    assert list_response.status_code == 200, f"Failed to list messages: {list_response.text}"
    
    response_json = list_response.json()
    assert "messages" in response_json
    messages = response_json["messages"]

    assert isinstance(messages, list)
    assert len(messages) > 0, "Should have at least one message in the conversation."
    
    # Check if our created message is in the list
    found_message = any(m["id"] == message_data["id"] for m in messages)
    assert found_message, "The newly created message was not found in the conversation's message list."
    
    print(f"Successfully listed messages and found the new message.")


@skip_if_no_backend
def test_full_message_response_flow(client: httpx.Client, authenticated_user, test_conversation):
    """
    Tests the full flow from sending a message, simulating a Brain callback,
    and retrieving the final AI response and its pipeline data.
    """
    conversation_id = test_conversation["id"]
    user_id = authenticated_user["user"]["id"]
    
    # 1. Create a user message
    print("\n--- Testing Full Flow: Creating User Message ---")
    user_message_content = "Tell me about black holes."
    message_payload = {
        "content": user_message_content,
        "purpose": "test"
    }
    create_response = client.post(f"/api/conversations/{conversation_id}/messages", json=message_payload)
    assert create_response.status_code == 200
    user_message_data = create_response.json()["message"]
    user_message_id = user_message_data["id"]
    print(f"Successfully created user message with ID: {user_message_id}")

    # 2. Simulate Brain service callback
    print(f"\n--- Testing Full Flow: Simulating Brain Callback for message {user_message_id} ---")
    ai_response_content = "Black holes are regions of spacetime where gravity is so strong that nothing can escape."
    pipeline_steps = [
        {"step": "Intent Recognition", "details": "User is asking an educational question."},
        {"step": "Knowledge Retrieval", "details": "Retrieved basic facts about black holes."},
        {"step": "Response Generation", "details": "Generated a concise definition."}
    ]
    brain_payload = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "original_message_id": user_message_id,
        "llm_response": ai_response_content,
        "pipeline_data": {
            "steps": pipeline_steps,
            "some_other_data": "some_value"
        },
        "prompt_version_id": 1 
    }
    
    # This is an internal endpoint and doesn't require user auth headers
    # We use a separate client instance or reuse the existing one without auth if it's set up that way.
    # The fixture `client` is already authenticated, but this endpoint should ignore it.
    callback_response = client.post("/api/internal/brain_response", json=brain_payload)
    assert callback_response.status_code == 202, f"Brain callback failed: {callback_response.text}"
    print("Successfully simulated Brain callback.")

    # 3. Poll for the AI response
    print(f"\n--- Testing Full Flow: Polling for AI Response for message {user_message_id} ---")
    ai_response_data = None
    for _ in range(10): # Poll for up to 5 seconds
        import time
        time.sleep(0.5)
        poll_response = client.get(f"/api/messages/{user_message_id}/response")
        if poll_response.status_code == 200 and poll_response.text:
            ai_response_data = poll_response.json()
            break
    
    assert ai_response_data is not None, "AI response was not found after polling."
    assert ai_response_data["content"] == ai_response_content
    assert ai_response_data["is_user"] is False
    ai_message_id = ai_response_data["id"]
    print(f"Successfully retrieved AI response with ID: {ai_message_id}")

    # 4. Verify the pipeline steps
    print(f"\n--- Testing Full Flow: Verifying Pipeline Steps for AI message {ai_message_id} ---")
    pipeline_response = client.get(f"/api/messages/{ai_message_id}/pipeline_steps")
    assert pipeline_response.status_code == 200, f"Failed to get pipeline steps: {pipeline_response.text}"
    retrieved_steps = pipeline_response.json()
    assert retrieved_steps == pipeline_steps
    print("Successfully verified pipeline steps.") 