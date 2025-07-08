import httpx
import pytest
import os

# Pytest marker for skipping tests if the backend URL is not set
skip_if_no_backend = pytest.mark.skipif(not os.getenv("BACKEND_API_URL"),
                                        reason="BACKEND_API_URL not set in .env file")


@skip_if_no_backend
def test_user_persona_upsert(client: httpx.Client, authenticated_user: dict):
    """
    Tests creating and then updating a user persona.
    """
    user_id = authenticated_user["user"]["id"]

    # 1. Create a new persona for this user.
    create_persona_payload = {
        "user_id": user_id,
        "persona_data": {"summary": "This is the initial persona."}
    }
    create_response = client.post("/api/user-personas", json=create_persona_payload)
    assert create_response.status_code == 200, f"Failed to create persona: {create_response.text}"
    persona = create_response.json()
    assert persona["user_id"] == user_id
    assert persona["persona_data"]["summary"] == "This is the initial persona."

    # 2. Update the existing persona.
    update_persona_payload = {
        "user_id": user_id,
        "persona_data": {"summary": "This is the updated persona."}
    }
    update_response = client.post("/api/user-personas", json=update_persona_payload)
    assert update_response.status_code == 200, f"Failed to update persona: {update_response.text}"
    updated_persona = update_response.json()
    assert updated_persona["user_id"] == user_id
    assert updated_persona["persona_data"]["summary"] == "This is the updated persona."
    assert updated_persona["id"] == persona["id"]  # The ID should be the same.


@skip_if_no_backend
def test_trigger_persona_generation_for_user(client: httpx.Client, authenticated_user: dict):
    """
    Tests triggering persona generation for a specific user.
    """
    user_id = authenticated_user["user"]["id"]
    
    # Trigger the task for the specific user
    response = client.post(
        "/api/tasks/trigger-user-persona-generation",
        json={"user_id": user_id}
    )
    
    assert response.status_code == 202, f"Trigger endpoint failed: {response.text}"
    json_response = response.json()
    assert f"Task to generate user personas has been queued for 1 users from user ID {user_id}" in json_response["message"]


@skip_if_no_backend
def test_trigger_persona_generation_batch(client: httpx.Client, authenticated_user: dict):
    """
    Tests triggering persona generation for all eligible users.
    This test creates the necessary preconditions for an existing user
    to be eligible for persona generation (having a memory).
    """
    # 1. Create a conversation to associate a memory with.
    create_convo_response = client.post("/api/conversations", json={"title": "Test Convo for Persona Batch"})
    assert create_convo_response.status_code == 201
    conversation = create_convo_response.json()
    conversation_id = conversation["id"]

    # 2. Create a memory for that conversation, making the user eligible.
    client.post(
        "/api/memories", 
        json={
            "conversation_id": conversation_id,
            "memory_data": {"summary": "A memory to make the user eligible."}
        }
    ).raise_for_status()

    # 3. Trigger the batch persona generation task.
    response = client.post(
        "/api/tasks/trigger-user-persona-generation",
        json={} # No user_id to trigger batch mode
    )
    
    assert response.status_code == 202, f"Trigger endpoint failed: {response.text}"
    json_response = response.json()
    assert "Task to generate user personas has been queued" in json_response["message"]
    assert "all eligible users" in json_response["message"] 