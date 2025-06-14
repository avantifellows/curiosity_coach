import httpx
import pytest
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BACKEND_API_URL = os.getenv("BACKEND_API_URL")

# Pytest marker for skipping tests if the backend URL is not set
skip_if_no_backend = pytest.mark.skipif(not BACKEND_API_URL,
                                        reason="BACKEND_API_URL not set in .env file")


@skip_if_no_backend
def test_conversation_crud_flow(client: httpx.Client, authenticated_user):
    """
    Tests the full CRUD (Create, Read, Update, Delete) flow for conversations
    in a single, sequential test to avoid state issues between tests.
    """
    user_id = authenticated_user["user"]["id"]
    
    # 1. Create Conversation
    print("\n--- Testing Conversation Creation ---")
    create_payload = {"title": "My CRUD Test Conversation"}
    create_response = client.post("/api/conversations", json=create_payload)
    assert create_response.status_code == 201, f"Failed to create conversation: {create_response.text}"
    conversation_data = create_response.json()
    assert "id" in conversation_data
    conversation_id = conversation_data["id"]
    print(f"Successfully created conversation with ID: {conversation_id}")

    # Add a small delay to allow for potential database commit/replication lag
    time.sleep(1)

    # 2. Read (List) Conversations and verify creation
    print(f"\n--- Testing Reading Conversations ---")
    get_response = client.get(f"/api/conversations")
    assert get_response.status_code == 200, f"Failed to get conversations: {get_response.text}"
    conversations_list = get_response.json()
    assert any(c["id"] == conversation_id for c in conversations_list)
    print(f"Successfully found conversation {conversation_id} in the user's list.")

    # 2b. Read (Single) Conversation
    print(f"--- Testing Reading Conversation {conversation_id} ---")
    get_single_response = client.get(f"/api/conversations/{conversation_id}")
    assert get_single_response.status_code == 200, f"Failed to get conversation {conversation_id}: {get_single_response.text}"
    single_conversation_data = get_single_response.json()
    assert single_conversation_data["id"] == conversation_id
    assert single_conversation_data["title"] == "My CRUD Test Conversation" # Before update
    print(f"Successfully read single conversation with ID: {conversation_id}")


    # 3. Update Conversation
    print(f"\n--- Testing Updating Conversation {conversation_id} ---")
    update_payload = {"title": "My Updated CRUD Conversation"}
    update_response = client.put(f"/api/conversations/{conversation_id}/title", json=update_payload)
    assert update_response.status_code == 200, f"Failed to update conversation: {update_response.text}"
    updated_data = update_response.json()
    assert updated_data["title"] == "My Updated CRUD Conversation"
    assert updated_data["id"] == conversation_id
    print(f"Successfully updated conversation with ID: {conversation_id}")

    # 4. Delete Conversation
    print(f"\n--- Testing Deleting Conversation {conversation_id} ---")
    delete_response = client.delete(f"/api/conversations/{conversation_id}")
    assert delete_response.status_code == 204, f"Failed to delete conversation: {delete_response.text}"
    print(f"Successfully deleted conversation with ID: {conversation_id}")

    # 5. Verify Deletion
    print(f"\n--- Verifying Deletion of Conversation {conversation_id} ---")
    get_response_after_delete = client.get("/api/conversations")
    assert get_response_after_delete.status_code == 200
    conversations_after_delete = get_response_after_delete.json()
    assert not any(c["id"] == conversation_id for c in conversations_after_delete)
    print(f"Successfully verified conversation {conversation_id} is no longer in the list.") 