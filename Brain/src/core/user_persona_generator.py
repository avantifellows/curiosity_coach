import json
import os
from src.services.api_service import api_service
from src.services.llm_service import LLMService
from src.utils.logger import logger
from src.schemas import UserPersonaData

# Define paths relative to this file's location
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_USER_PERSONA_GENERATION_PROMPT_PATH = os.path.join(_PROMPT_DIR, "user_persona_generation_prompt.txt")

async def generate_persona_for_user(user_id: int):
    """
    Generates a user persona based on their conversation memories and saves it.
    """
    logger.info(f"Starting persona generation for user_id: {user_id}")

    # 1. Fetch conversation memories
    memories = await api_service.get_conversation_memories_for_user(user_id)
    if not memories:
        logger.warning(f"No conversation memories found for user {user_id}. Skipping persona generation.")
        return

    logger.info(f"Found {len(memories)} memories for user {user_id}.")

    # 2. Prepare the prompt for the LLM
    try:
        with open(_USER_PERSONA_GENERATION_PROMPT_PATH, "r") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error(f"Persona generation prompt file not found at {_USER_PERSONA_GENERATION_PROMPT_PATH}.")
        return

    # The prompt expects a JSON object with a "memories" key
    # The memories from the API are expected to be a list of dicts,
    # where each dict has the conversation memory data.
    memories_payload = {"memories": memories}
    
    final_prompt = f"{prompt_template}\n\n{json.dumps(memories_payload, indent=2)}"
    
    messages = [{"role": "user", "content": final_prompt}]

    # 3. Call the LLM to get the persona
    try:
        llm_service = LLMService()
        logger.info(f"Calling LLM for persona generation for user {user_id}.")
        # Use json_mode to enforce a JSON response
        raw_response = llm_service.get_completion(
            messages,
            call_type="user_persona_generation",
            json_mode=True
        )
        
        # Now we can directly parse the response
        persona_data = json.loads(raw_response)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from LLM response for user {user_id}. Error: {e}")
        logger.debug(f"Raw LLM response was: {raw_response}")
        return
    except Exception as e:
        logger.error(f"An error occurred during LLM call for user {user_id}: {e}")
        return

    # 4. Validate the response against schema and save to DB
    try:
        validated_persona = UserPersonaData(**persona_data)
    except Exception as e:
        logger.warning(f"UserPersonaData validation failed for user {user_id}: {e}")
        logger.debug(f"Received data: {persona_data}")
        return

    logger.info(f"Successfully generated persona for user {user_id}.")
    
    success = await api_service.post_user_persona(user_id=user_id, persona_data=validated_persona.model_dump())

    if success:
        logger.info(f"Successfully saved persona for user {user_id}.")
    else:
        logger.error(f"Failed to save persona for user {user_id}.") 