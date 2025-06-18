import httpx
import pytest
import os
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BACKEND_API_URL = os.getenv("BACKEND_API_URL")

# Pytest marker for skipping tests if the backend URL is not set
skip_if_no_backend = pytest.mark.skipif(not BACKEND_API_URL,
                                        reason="BACKEND_API_URL not set in .env file")


@pytest.fixture(scope="function")
def test_prompt(client: httpx.Client):
    """
    Fixture to create a new prompt for testing.
    Cleans up the prompt after the test.
    """
    prompt_name = f"test-prompt-{uuid.uuid4()}"
    print(f"--- Fixture: Creating prompt '{prompt_name}' ---")
    create_payload = {
        "name": prompt_name,
        "description": "A prompt for CRUD testing."
    }
    response = client.post("/api/prompts", json=create_payload)
    assert response.status_code == 201
    prompt_data = response.json()
    
    yield prompt_data
    
    # Teardown: delete the prompt
    print(f"--- Fixture: Deleting prompt ID {prompt_data['id']} ---")
    delete_response = client.delete(f"/api/prompts/{prompt_data['id']}")
    # Allow 404 in case the test deleted it
    assert delete_response.status_code in [204, 404]


@skip_if_no_backend
class TestPromptCRUD:
    def test_create_and_get_prompt(self, client: httpx.Client, test_prompt):
        """ Tests creating and then fetching a single prompt. """
        prompt_id = test_prompt["id"]
        prompt_name = test_prompt["name"]
        
        # Get by ID
        print(f"--- Test: Getting prompt by ID {prompt_id} ---")
        get_response = client.get(f"/api/prompts/{prompt_id}")
        assert get_response.status_code == 200
        fetched_prompt = get_response.json()
        assert fetched_prompt["id"] == prompt_id
        assert fetched_prompt["name"] == prompt_name

        # Get by Name
        print(f"--- Test: Getting prompt by name '{prompt_name}' ---")
        get_response_by_name = client.get(f"/api/prompts/{prompt_name}")
        assert get_response_by_name.status_code == 200
        fetched_prompt_by_name = get_response_by_name.json()
        assert fetched_prompt_by_name["id"] == prompt_id

    def test_update_prompt(self, client: httpx.Client, test_prompt):
        """ Tests updating a prompt's name and description. """
        prompt_id = test_prompt["id"]
        
        print(f"--- Test: Updating prompt {prompt_id} ---")
        update_payload = {
            "name": f"updated-name-{uuid.uuid4()}",
            "description": "This prompt has been updated."
        }
        update_response = client.put(f"/api/prompts/{prompt_id}", json=update_payload)
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        updated_prompt = update_response.json()
        assert updated_prompt["name"] == update_payload["name"]
        assert updated_prompt["description"] == update_payload["description"]

    def test_list_prompts(self, client: httpx.Client, test_prompt):
        """ Tests listing prompts and finding the test prompt. """
        prompt_id = test_prompt["id"]
        
        print("--- Test: Listing all prompts ---")
        list_response = client.get("/api/prompts")
        assert list_response.status_code == 200
        prompts_list = list_response.json()
        assert isinstance(prompts_list, list)
        assert any(p["id"] == prompt_id for p in prompts_list)
        print("Successfully found test prompt in the list.")

    def test_delete_prompt(self, client: httpx.Client, test_prompt):
        """ Tests deleting a prompt. """
        prompt_id = test_prompt["id"]
        
        print(f"--- Test: Deleting prompt {prompt_id} ---")
        delete_response = client.delete(f"/api/prompts/{prompt_id}")
        assert delete_response.status_code == 204
        
        # Verify it's gone
        get_response = client.get(f"/api/prompts/{prompt_id}")
        assert get_response.status_code == 404
        print("Successfully deleted prompt and verified its removal.")


@skip_if_no_backend
class TestPromptVersionManagement:

    def test_version_crud_and_activation(self, client: httpx.Client, test_prompt, authenticated_user):
        """
        Tests creating, listing, setting active, and getting active versions of a prompt.
        """
        prompt_id = test_prompt["id"]
        user_id = authenticated_user["user"]["id"]

        # 1. Create first version
        print(f"--- Test: Creating first version for prompt {prompt_id} ---")
        v1_payload = {"prompt_text": "This is version 1."}
        v1_response = client.post(f"/api/prompts/{prompt_id}/versions", json=v1_payload)
        assert v1_response.status_code == 201, f"Failed to create V1: {v1_response.text}"
        v1_data = v1_response.json()
        assert v1_data["version_number"] == 1
        assert v1_data["prompt_text"] == "This is version 1."
        v1_id = v1_data["id"]

        # 2. Create second version
        print(f"--- Test: Creating second version for prompt {prompt_id} ---")
        v2_payload = {"prompt_text": "This is version 2, which will be active."}
        v2_response = client.post(f"/api/prompts/{prompt_id}/versions", json=v2_payload)
        assert v2_response.status_code == 201, f"Failed to create V2: {v2_response.text}"
        v2_data = v2_response.json()
        assert v2_data["version_number"] == 2
        v2_id = v2_data["id"]

        # 3. List versions
        print(f"--- Test: Listing versions for prompt {prompt_id} ---")
        list_response = client.get(f"/api/prompts/{prompt_id}/versions")
        assert list_response.status_code == 200
        versions_list = list_response.json()
        assert len(versions_list) == 2
        assert any(v["id"] == v1_id for v in versions_list)
        assert any(v["id"] == v2_id for v in versions_list)

        # 4. Set V2 as active
        print(f"--- Test: Setting version {v2_id} as active for prompt {prompt_id} ---")
        set_active_payload = {"version_id": v2_id}
        set_active_response = client.post(f"/api/prompts/{prompt_id}/versions/set-active", json=set_active_payload)
        assert set_active_response.status_code == 200, f"Failed to set active: {set_active_response.text}"
        
        # 5. Get active version and verify it's V2
        print(f"--- Test: Getting active version for prompt {prompt_id} ---")
        get_active_response = client.get(f"/api/prompts/{prompt_id}/versions/active")
        assert get_active_response.status_code == 200
        active_version = get_active_response.json()
        assert active_version["id"] == v2_id
        assert active_version["prompt_text"] == "This is version 2, which will be active."

    def test_production_version_flow(self, client: httpx.Client, test_prompt, authenticated_user):
        """
        Tests setting, getting, and unsetting a production version.
        """
        prompt_id = test_prompt["id"]
        
        # Create a version to be production
        print(f"--- Test: Creating a version for production test on prompt {prompt_id} ---")
        prod_payload = {"prompt_text": "This is the production version."}
        prod_response = client.post(f"/api/prompts/{prompt_id}/versions", json=prod_payload)
        assert prod_response.status_code == 201
        prod_data = prod_response.json()
        version_number = prod_data["version_number"]

        # Set it as production
        print(f"--- Test: Setting version {version_number} as production ---")
        set_prod_response = client.post(f"/api/prompts/{prompt_id}/versions/{version_number}/set-production")
        assert set_prod_response.status_code == 200, f"Failed to set production: {set_prod_response.text}"
        assert set_prod_response.json()["is_production"] is True

        # Get production version and verify
        print("--- Test: Getting production version ---")
        get_prod_response = client.get(f"/api/prompts/{prompt_id}/versions/production")
        assert get_prod_response.status_code == 200
        assert get_prod_response.json()["id"] == prod_data["id"]

        # Unset production flag
        print(f"--- Test: Unsetting production status for version {version_number} ---")
        unset_prod_response = client.delete(f"/api/prompts/{prompt_id}/versions/{version_number}/unset-production")
        assert unset_prod_response.status_code == 200, f"Failed to unset production: {unset_prod_response.text}"
        assert unset_prod_response.json()["is_production"] is False

        # Verify it's no longer the production version
        get_prod_again_response = client.get(f"/api/prompts/{prompt_id}/versions/production")
        assert get_prod_again_response.status_code == 404 