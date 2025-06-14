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

# Singleton instance
api_service = APIService() 