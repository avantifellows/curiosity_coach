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


@skip_if_no_backend
def test_generate_memory_for_single_conversation_and_internal_read(client: httpx.Client):
    # Create conversation and add a message
    convo_resp = client.post("/api/conversations", json={"title": "Single Conv"})
    assert convo_resp.status_code == 201
    conversation_id = convo_resp.json()["id"]

    msg_resp = client.post(f"/api/conversations/{conversation_id}/messages", json={"conversation_id": conversation_id, "content": "Hello", "is_user": True})
    assert msg_resp.status_code == 200

    # Trigger sync generation for this conversation (local mode expected)
    gen_resp = client.post(f"/api/tasks/generate-memory-for-conversation/{conversation_id}?sync=true")
    assert gen_resp.status_code in (200, 202)

    # We cannot guarantee memory is generated in non-local env; just call internal read and allow 404 or 200
    read_resp = client.get(f"/api/internal/conversations/{conversation_id}/memory")
    assert read_resp.status_code in (200, 404)


@skip_if_no_backend
def test_generate_memories_for_user_with_filters(client: httpx.Client):
    # Create conversation for a new user via login flow or use existing test helper if any
    # Here we just create a conversation which will be associated with default test user in fixtures
    convo_resp = client.post("/api/conversations", json={"title": "User Scoped"})
    assert convo_resp.status_code == 201
    conversation_id = convo_resp.json()["id"]

    # Add a message
    client.post(f"/api/conversations/{conversation_id}/messages", json={"conversation_id": conversation_id, "content": "Hi", "is_user": True})

    # We need a user_id; attempt to read from /api/auth/me using default auth header from fixture
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    user_id = me_resp.json()["id"]

    # Trigger user-scoped generation (only_needing=true, include_empty=false, clamp=1, sync=false)
    trigger_resp = client.post(f"/api/tasks/generate-memories-for-user/{user_id}?only_needing=true&include_empty=false&clamp=1")
    assert trigger_resp.status_code in (200, 202)