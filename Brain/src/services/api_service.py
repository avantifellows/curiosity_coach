import httpx
import os
from typing import Dict, Any, List, Optional
from src.utils.logger import logger

class APIService:
    def __init__(self):
        self.backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
        logger.info(f"APIService initialized with backend_url: {self.backend_url}")

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
            # Use explicit timeout (30 seconds) to avoid hanging
            timeout = httpx.Timeout(30.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Saving memory to: {url}")
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info(f"Successfully saved memory for conversation {conversation_id}")
                return True
        except httpx.TimeoutException as e:
            logger.error(f"Timeout saving memory for conversation {conversation_id}: {e}", exc_info=True)
            return False
        except httpx.RequestError as e:
            logger.error(f"Request error saving memory for conversation {conversation_id}: {type(e).__name__}: {e}", exc_info=True)
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error while saving memory for conversation {conversation_id}: {e.response.text}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving memory for conversation {conversation_id}: {type(e).__name__}: {e}", exc_info=True)
            return False

    async def get_conversation_history(self, conversation_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches the full conversation history from the backend.
        """
        url = f"{self.backend_url}/api/internal/conversations/{conversation_id}/messages_for_brain"
        try:
            # Use explicit timeout (30 seconds) to avoid hanging
            timeout = httpx.Timeout(30.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Fetching conversation history from: {url}")
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                if data.get("success"):
                    logger.info(f"Successfully fetched {len(data.get('messages', []))} messages for conversation {conversation_id}")
                    return data.get("messages", [])
                else:
                    logger.warning(f"Backend indicated failure fetching history for conv {conversation_id}: {data.get('message')}")
                    return None
        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching conversation history for {conversation_id}: {e}", exc_info=True)
            return None
        except httpx.ConnectError as e:
            logger.error(f"Connection error fetching conversation history for {conversation_id}. Backend URL: {url}. Error: {type(e).__name__}: {e}", exc_info=True)
            logger.error(f"Is the backend running on {self.backend_url}?")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching conversation history for {conversation_id}: {type(e).__name__}: {e}", exc_info=True)
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error while fetching history for {conversation_id}: {e.response.text}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching conversation history for {conversation_id}: {type(e).__name__}: {e}", exc_info=True)
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
        Also augments it with student metadata (name) for use in prompts.
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
                persona_data = response.json().get("persona_data")
                
                # Augment persona with student name for prompt injection
                if persona_data:
                    student = await self.get_student_by_user_id(user_id)
                    if student:
                        persona_data["_student_name"] = student.get("first_name")
                        logger.info(f"Augmented persona with student name: {student.get('first_name')}")
                
                return persona_data
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

    async def get_conversation_prompt(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch the prompt text for a conversation's assigned prompt version.
        Used for opening message generation.
        
        Returns:
            Dict with keys: prompt_text, version_number, prompt_id
            None if conversation or prompt not found
        """
        url = f"{self.backend_url}/api/internal/conversations/{conversation_id}/prompt"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 404:
                    logger.warning(f"No prompt found for conversation {conversation_id}")
                    return None
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Error fetching conversation prompt for {conversation_id}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while fetching prompt for {conversation_id}: {e.response.text}")
            return None

    async def get_previous_memories(
        self, 
        user_id: int, 
        exclude_conversation_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all previous conversation memories for a user.
        Excludes the specified conversation (current one).
        Returns list of memory data objects ordered chronologically.
        
        Returns:
            List of memory_data dictionaries (empty list if none found)
        """
        url = f"{self.backend_url}/api/internal/users/{user_id}/previous-memories"
        params = {}
        if exclude_conversation_id:
            params["exclude_conversation_id"] = exclude_conversation_id
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                # Extract memory_data from each memory object
                return [mem["memory_data"] for mem in data.get("memories", [])]
        except httpx.RequestError as e:
            logger.warning(f"Error fetching previous memories for user {user_id}: {e}")
            return []  # Return empty list on error (graceful degradation)
        except httpx.HTTPStatusError as e:
            logger.warning(f"Error response {e.response.status_code} while fetching previous memories: {e.response.text}")
            return []

    async def get_student_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch student record by user_id.
        
        Returns:
            Student dict with id, user_id, school, grade, etc. or None if not found
        """
        url = f"{self.backend_url}/api/internal/users/{user_id}/student"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 404:
                    logger.warning(f"No student record found for user_id {user_id}")
                    return None
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Error fetching student for user {user_id}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while fetching student for user {user_id}: {e.response.text}")
            return None

    async def get_student_conversation_transcript(self, student_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch formatted conversation transcripts for a student.
        Used by Brain for persona generation.
        
        Returns:
            Dict with {"transcript": str, "conversation_count": int} or None if error
        """
        url = f"{self.backend_url}/api/internal/student-transcript/{student_id}"
        try:
            timeout = httpx.Timeout(60.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Fetching conversation transcript from: {url}")
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                conversation_count = data.get("conversation_count", 0)
                logger.info(f"Successfully fetched transcript for student {student_id}: {conversation_count} conversations")
                return data
        except httpx.RequestError as e:
            logger.error(f"Error fetching conversation transcript for student {student_id}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while fetching transcript for student {student_id}: {e.response.text}")
            return None

    async def get_class_conversation_transcript(self, school: str, grade: int, section: Optional[str] = None) -> Optional[str]:
        """
        Fetch formatted conversation transcripts for a class.
        Used by Brain for class analysis.
        
        Returns:
            Formatted transcript string or None if error
        """
        url = f"{self.backend_url}/api/internal/class-transcript"
        params = {"school": school, "grade": grade}
        if section:
            params["section"] = section
        
        try:
            timeout = httpx.Timeout(60.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Fetching class transcript from: {url} with params: {params}")
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                transcript = data.get("transcript", "")
                student_count = data.get("student_count", 0)
                conversation_count = data.get("conversation_count", 0)
                logger.info(f"Successfully fetched class transcript: {student_count} students, {conversation_count} conversations")
                return transcript
        except httpx.RequestError as e:
            logger.error(f"Error fetching class transcript: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while fetching class transcript: {e.response.text}")
            return None

    async def send_analysis_callback(self, callback_url: str, payload: Dict[str, Any]) -> bool:
        """
        Send analysis callback to backend.
        Used for class and student analysis tasks.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            timeout = httpx.Timeout(30.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Sending analysis callback to {callback_url}")
                response = await client.post(callback_url, json=payload)
                response.raise_for_status()
                logger.info(f"Successfully sent callback for job {payload.get('job_id')}")
                return True
        except httpx.RequestError as e:
            logger.error(f"Error sending callback: {e}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} sending callback: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending callback: {e}")
            return False

    async def get_prompt_template(self, prompt_name: str, prefer_production: bool = True) -> Optional[str]:
        """
        Fetch prompt template from backend.
        Tries production version first (if prefer_production=True), then falls back to active.
        
        Returns:
            Prompt text string or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try production first (or active if prefer_production=False)
                if prefer_production:
                    version_url = f"{self.backend_url}/api/prompts/{prompt_name}/versions/production"
                    logger.info(f"Fetching production prompt '{prompt_name}' from {version_url}")
                    response = await client.get(version_url)
                    
                    if response.status_code == 200:
                        data = response.json()
                        prompt_text = data.get("prompt_text")
                        if prompt_text:
                            logger.info(f"Successfully fetched production prompt '{prompt_name}'")
                            return prompt_text
                    
                    # Fall back to active
                    logger.info(f"Production not found for '{prompt_name}', trying active version")
                
                # Try active version
                active_url = f"{self.backend_url}/api/prompts/{prompt_name}/versions/active"
                logger.info(f"Fetching active prompt '{prompt_name}' from {active_url}")
                response = await client.get(active_url)
                
                if response.status_code == 200:
                    data = response.json()
                    prompt_text = data.get("prompt_text")
                    if prompt_text:
                        logger.info(f"Successfully fetched active prompt '{prompt_name}'")
                        return prompt_text
                
                logger.warning(f"Prompt '{prompt_name}' not found in backend (tried production and active)")
                return None
                
        except httpx.RequestError as e:
            logger.error(f"Error fetching prompt '{prompt_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching prompt '{prompt_name}': {e}")
            return None

    async def get_user_conversations(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch list of conversation IDs for a user.
        Used by Brain to check conversation count before persona generation.
        
        Returns:
            Dict with keys: user_id, conversation_count, conversation_ids
            None if error
        """
        url = f"{self.backend_url}/api/internal/users/{user_id}/conversations"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Error fetching conversations for user {user_id}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response {e.response.status_code} while fetching conversations for user {user_id}: {e.response.text}")
            return None

    async def get_conversation_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all messages for a conversation (for idempotency check in opening message).
        
        Returns:
            List of message dictionaries (empty list if none found or error)
        """
        url = f"{self.backend_url}/api/internal/conversations/{conversation_id}/messages_for_brain"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return data.get("messages", []) if data.get("success") else []
        except Exception as e:
            logger.warning(f"Error fetching messages for conversation {conversation_id}: {e}")
            return []
        
    async def get_conversation_core_theme(self, conversation_id: int) -> Optional[str]:
        """
        Fetch the core theme for a specific conversation from the backend.
        """
        try:
            backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
            url = f"{backend_url}/api/internal/conversations/{conversation_id}/core-theme"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return data.get("core_theme")
        except Exception as e:
            logger.error(f"Error fetching core theme for conversation {conversation_id}: {e}")
            return None    

    async def get_conversation_messages_with_pipeline(self, conversation_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all messages for a conversation WITH their pipeline data.
        
        Returns:
            List of message dictionaries with pipeline_data included
        """
        url = f"{self.backend_url}/api/internal/conversations/{conversation_id}/messages_with_pipeline"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return data.get("messages", []) if data.get("success") else []
        except Exception as e:
            logger.warning(f"Error fetching messages with pipeline for conversation {conversation_id}: {e}")
            return []
        
    async def get_production_prompt_version(self, prompt_name: str) -> Dict[str, Any]:
        url = f"{self.backend_url}/api/prompts/{prompt_name}/versions/production"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()

        
    async def post_generic_flow_items(self, flow_slug: str, conversation_id: int, items: list) -> bool:
        url = f"{self.backend_url}/api/internal/analytics/{flow_slug}/{conversation_id}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                await client.post(url, headers={"Content-Type": "application/json"}, json={"items": items})
            return True
        except Exception as e:
            logger.error(f"Error posting items for flow {flow_slug} (conversation {conversation_id}): {e}")
            return False 


# Singleton instance
api_service = APIService() 