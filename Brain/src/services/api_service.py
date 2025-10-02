import httpx
import os
from typing import Dict, Any, List, Optional
from src.utils.logger import logger

class APIService:
    def __init__(self):
        self.backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")

    async def save_memory(self, conversation_id: int, memory_data: Dict[str, Any]) -> bool:
        """
        Saves the generated memory for a conversation to the backend.
        """
        url = f"{self.backend_url}/api/memories"
        payload = {
            "conversation_id": conversation_id,
            "memory_data": memory_data
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info(f"Successfully saved memory for conversation {conversation_id}")
                return True
        except httpx.RequestError as e:
            logger.error(f"Error saving memory for conversation {conversation_id}: {e}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while saving memory for conversation {conversation_id}: {e.response.text}")
            return False

    async def get_conversation_history(self, conversation_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches the full conversation history from the backend.
        """
        url = f"{self.backend_url}/api/internal/conversations/{conversation_id}/messages_for_brain"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                if data.get("success"):
                    return data.get("messages", [])
                else:
                    logger.warning(f"Backend indicated failure fetching history for conv {conversation_id}: {data.get('message')}")
                    return None
        except httpx.RequestError as e:
            logger.error(f"Error fetching conversation history for {conversation_id}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while fetching history for {conversation_id}: {e.response.text}")
            return None

    async def get_conversation_memories_for_user(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches all conversation memories for a specific user from the backend.
        """
        url = f"{self.backend_url}/api/internal/users/{user_id}/memories"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                # Assuming the endpoint returns a list of memories directly
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Error fetching conversation memories for user {user_id}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while fetching memories for user {user_id}: {e.response.text}")
            return None

    async def get_conversation_memory(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single conversation's memory_data via internal endpoint.
        Returns the memory_data dict or None if not found (404).
        """
        url = f"{self.backend_url}/api/internal/conversations/{conversation_id}/memory"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 404:
                    logger.info(f"No memory found for conversation {conversation_id}.")
                    return None
                response.raise_for_status()
                data = response.json()
                return data.get("memory_data")
        except httpx.RequestError as e:
            logger.error(f"Error fetching memory for conversation {conversation_id}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while fetching memory for conversation {conversation_id}: {e.response.text}")
            return None

    async def get_user_persona(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetches the user persona for a specific user from the backend.
        """
        # Note: This endpoint is hypothetical and needs to be implemented in the backend.
        url = f"{self.backend_url}/api/internal/users/{user_id}/persona"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 404:
                    logger.info(f"No persona found for user {user_id}.")
                    return None
                response.raise_for_status()
                # Assuming the endpoint returns the persona data directly
                return response.json().get("persona_data")
        except httpx.RequestError as e:
            logger.error(f"Error fetching user persona for user {user_id}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while fetching persona for user {user_id}: {e.response.text}")
            return None

    async def post_user_persona(self, user_id: int, persona_data: Dict[str, Any]) -> bool:
        """
        Posts the generated user persona to the backend.
        """
        url = f"{self.backend_url}/api/user-personas"
        payload = {
            "user_id": user_id,
            "persona_data": persona_data
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info(f"Successfully posted persona for user {user_id}")
                return True
        except httpx.RequestError as e:
            logger.error(f"Error posting persona for user {user_id}: {e}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while posting persona for user {user_id}: {e.response.text}")
            return False

# Singleton instance
api_service = APIService() 