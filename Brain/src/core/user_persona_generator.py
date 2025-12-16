import json
from src.services.api_service import api_service
from src.services.llm_service import LLMService
from src.utils.logger import logger
from src.schemas import UserPersonaData


async def generate_persona_for_user(user_id: int):
    """
    Generates a user persona based on their conversation transcripts and saves it.
    Requires minimum 3 conversations for meaningful persona generation.
    """
    logger.info(f"Starting persona generation for user_id: {user_id}")

    # 1. Check minimum conversation count (requires at least 3 conversations)
    user_conversations = await api_service.get_user_conversations(user_id)
    if not user_conversations:
        logger.error(f"Failed to fetch conversations for user {user_id}. Skipping persona generation.")
        return
    
    conversation_count = user_conversations.get("conversation_count", 0)
    if conversation_count < 3:
        logger.info(f"User {user_id} has only {conversation_count} conversations. "
                   f"Persona generation requires minimum 3 conversations. Skipping.")
        return
    
    logger.info(f"User {user_id} has {conversation_count} conversations. Proceeding with persona generation.")

    # 2. Get student_id from user_id
    student = await api_service.get_student_by_user_id(user_id)
    if not student:
        logger.warning(f"No student record found for user {user_id}. Skipping persona generation.")
        return
    
    student_id = student.get("id")
    logger.info(f"Found student_id {student_id} for user_id {user_id}")

    # 3. Fetch conversation transcript using student_id
    transcript_data = await api_service.get_student_conversation_transcript(student_id)
    if not transcript_data:
        logger.warning(f"No conversation transcript found for student {student_id}. Skipping persona generation.")
        return
    
    transcript = transcript_data.get("transcript", "")
    if not transcript.strip():
        logger.warning(f"Empty conversation transcript for student {student_id}. Skipping persona generation.")
        return

    logger.info(f"Successfully fetched conversation transcript for student {student_id} (length: {len(transcript)} chars)")

    # 4. Fetch prompt from database
    prompt_template = await api_service.get_prompt_template("user_persona_generation")
    if not prompt_template:
        logger.error("Prompt 'user_persona_generation' not found in database. Skipping persona generation.")
        return

    # Replace the placeholder with actual transcript
    final_prompt = prompt_template.replace("{{CONVERSATION_TRANSCRIPTS}}", transcript)
    
    messages = [{"role": "user", "content": final_prompt}]

    # 5. Call the LLM to get the persona
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

    # 6. Validate the response against schema and save to DB
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