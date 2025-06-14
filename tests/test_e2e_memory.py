import httpx
import pytest
import os

# Pytest marker for skipping tests if the backend URL is not set
skip_if_no_backend = pytest.mark.skipif(not os.getenv("BACKEND_API_URL"),
                                        reason="BACKEND_API_URL not set in .env file")


@skip_if_no_backend
def test_memory_upsert_flow(client: httpx.Client):
    """
    Tests creating and then updating a conversation memory.
    """
    # 1. First, create a conversation to associate the memory with.
    create_convo_payload = {"title": "Test Conversation for Memory"}
    create_convo_response = client.post("/api/conversations", json=create_convo_payload)
    assert create_convo_response.status_code == 201, f"Failed to create conversation: {create_convo_response.text}"
    conversation = create_convo_response.json()
    conversation_id = conversation["id"]

    # 2. Create a new memory for this conversation.
    create_memory_payload = {
        "conversation_id": conversation_id,
        "memory_data": {"summary": "This is the initial summary.", "keywords": ["initial"]}
    }
    create_memory_response = client.post("/api/memories", json=create_memory_payload)
    assert create_memory_response.status_code == 200, f"Failed to create memory: {create_memory_response.text}"
    memory = create_memory_response.json()
    assert memory["conversation_id"] == conversation_id
    assert memory["memory_data"]["summary"] == "This is the initial summary."

    # 3. Update the existing memory for the same conversation.
    update_memory_payload = {
        "conversation_id": conversation_id,
        "memory_data": {"summary": "This is the updated summary.", "keywords": ["updated"]}
    }
    update_memory_response = client.post("/api/memories", json=update_memory_payload)
    assert update_memory_response.status_code == 200, f"Failed to update memory: {update_memory_response.text}"
    updated_memory = update_memory_response.json()
    assert updated_memory["conversation_id"] == conversation_id
    assert updated_memory["memory_data"]["summary"] == "This is the updated summary."
    assert updated_memory["id"] == memory["id"]  # The ID should remain the same.


@skip_if_no_backend
def test_trigger_memory_generation_endpoint(client: httpx.Client):
    """
    Tests that the trigger endpoint for memory generation runs successfully
    after creating a new conversation.

    NOTE: This is a limited test. It only confirms that the endpoint
    can be called and returns a success status. It does not verify that
    a memory was actually created for the new conversation, as that
    is an asynchronous process.
    """
    # 1. Create a conversation so there's something to process.
    create_convo_payload = {"title": "Test Convo for Memory Generation"}
    create_convo_response = client.post("/api/conversations", json=create_convo_payload)
    assert create_convo_response.status_code == 201
    conversation = create_convo_response.json()
    conversation_id = conversation["id"]

    # 2. Add a message to the conversation to make it "active".
    # The memory generation task looks for recently active conversations.
    message_payload = {
        "conversation_id": conversation_id,
        "content": "This is a test message to trigger activity.",
        "is_user": True
    }
    create_message_response = client.post(f"/api/conversations/{conversation_id}/messages", json=message_payload)
    assert create_message_response.status_code == 200

    # 3. Trigger the memory generation task.
    response = client.post("/api/tasks/trigger-memory-generation")
    
    assert response.status_code == 202, f"Trigger endpoint failed: {response.text}"
    
    # The test environment may or may not have other aged conversations.
    # We expect one of the success messages.
    json_response = response.json()
    assert ("No conversations found that require memory generation." in json_response["message"] or
            "Task to generate memories has been queued" in json_response["message"]) 