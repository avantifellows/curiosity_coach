# intent_response_generator.py

import os
from typing import Dict, Any, Tuple, Optional
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Define paths relative to this file's location
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


class ResponseGenerationError(Exception):
    """Custom exception for response generation errors"""
    pass


intent_prompt_templates = {
    "cognitive_intent": {
        "Concept Clarification": "Define the term in very simple language, relate it to a real-world analogy, and ask: 'Have you come across something like this before?'",
        "Causal Exploration": "Explain the reason behind the phenomenon step-by-step. Then end with a question like: 'Can you think of another place in the universe where this might also happen?'",
        "Comparison Seeking": "Give a contrast-based explanation with a table or analogy. Follow with: 'Which one do you think is cooler or more useful?'",
        "Hypothetical Reasoning": "Say: 'Let\'s imagine this was true… what would change around us?' and walk them through a scenario. End with: 'What else would you change in this imagined world?'",
        "Application Inquiry": "Start with: 'This might sound surprising, but this is used in real life like this…'. Then ask: 'Where else do you think this idea could be useful?'",
        "Depth Expansion": "Say: 'You already know the basics, so let\'s go one level deeper…'. Then offer an advanced idea and ask: 'Does this change how you see the original idea?'"
    },
    "exploratory_intent": {
        "Open-ended Exploration": "Give a fun fact or little-known detail and say: 'Want me to show you more fascinating stuff related to this?'",
        "Topic Hopping": "Mention 2–3 related ideas and ask: 'Want to jump into those next?'",
        "Curiosity about Systems/Structures": "Explain how the system\'s parts work together. Ask: 'What would happen if one part didn\'t work?'"
    },
    "metacognitive_intent": {
        "Learning How to Learn": "Give a technique or trick (e.g., memory method) and ask: 'Want to try using it on this topic?'",
        "Interest Reflection": "Link the topic to hobbies and say: 'Do you think this connects with what you already enjoy doing?'"
    },
    "emotional_identity_intent": {
        "Identity Exploration": "Say: 'It\'s okay to feel unsure. Let\'s explore this together step-by-step.' Then give an easy entry point.",
        "Validation Seeking": "Say: 'That\'s a great thought — let me show you if that\'s true and why.'",
        "Inspiration Seeking": "Respond with awe: 'This is mind-blowing — let me show you why!'"
    },
    "recursive_intent": {
        "Curiosity about Curiosity": "Say: 'Curiosity is like gravity for the mind.' Then ask: 'What\'s the last thing that really pulled your attention like that?'"
    },
    "conversational_intent": {
        "Greeting": "Warmly greet the student and ask what they're curious about today. For example: 'Hello! What scientific topic or question has been on your mind lately?'",
        "Small_Talk": "Briefly acknowledge the small talk, then guide toward learning with a question like: 'What have you been learning recently that you found interesting?' or 'Would you like to explore a fascinating science topic together?'",
        "Farewell": "Acknowledge the goodbye and encourage future curiosity with something like: 'Goodbye! Remember to stay curious and come back when you have more questions to explore!'",
        "Meaningless_Input": "Politely acknowledge the unclear input and offer structured options: 'I'm not quite sure what you're asking about. Would you like to learn about: 1) Space and astronomy, 2) Biology and living things, 3) How everyday technology works, or 4) Something else?'",
        "Meta_System_Query": "Briefly explain what Curiosity Coach does and offer a starter question: 'I'm here to help you explore interesting topics and answer your questions. What would you like to learn about today?'"
    }
}

def _generate_response_prompt(query: str, intent_data: Dict[str, Any], context_info: str) -> str:
    """
    Generates the prompt for the initial response based on query, intent, and context.
    """
    prompt_parts = []

    # Add student query
    prompt_parts.append(f"The student asked: \"{query}\"\n")
    
    # Check if intent_data has the expected structure
    if not intent_data or "intents" not in intent_data:
        # Handle missing intent data
        prompt_parts.append("This appears to be a query with unclear intent. Respond by:")
        prompt_parts.append("1. Acknowledging what was asked")
        prompt_parts.append("2. Providing a simple, friendly answer")
        prompt_parts.append("3. Asking a follow-up question to better understand their interests")
        prompt_parts.append("4. Encouraging further curiosity\n")
        
        # Add universal instructions and return
        prompt_parts.append("\nImportant guidelines:")
        prompt_parts.append("- Frame the response in a friendly, conversational tone aimed at a curious student aged 10-12")
        prompt_parts.append("- Keep responses concise (max 4-5 sentences)")
        prompt_parts.append("- Always end with a question that encourages further engagement")
        return "\n".join(prompt_parts)
    
    # Get primary intent from the intent structure
    primary_intent = intent_data.get("intents", {}).get("primary_intent", {})
    category = primary_intent.get("category", "")
    specific_type = primary_intent.get("specific_type", "")
    confidence = primary_intent.get("confidence", 0.0)
    
    # Extract context information from intent data
    student_context = intent_data.get("context", {})
    known_information = student_context.get("known_information", "Not specified")
    motivation = student_context.get("motivation", "Not specified")
    learning_goal = student_context.get("learning_goal", "Not specified")
    
    # Handle very low confidence or meaningless inputs differently
    if confidence < 0.4 or (category == "conversational_intent" and specific_type == "Meaningless_Input"):
        prompt_parts.append("This appears to be a low-quality or unclear input. Respond by:")
        prompt_parts.append("1. Briefly acknowledging what was said")
        prompt_parts.append("2. Redirecting to more meaningful conversation")
        prompt_parts.append("3. Offering 3-4 specific topic options they might be interested in")
        prompt_parts.append("4. Asking an engaging question to spark curiosity\n")
    
    # Add context for substantive questions
    elif category != "conversational_intent" and context_info and context_info.strip(): 
        prompt_parts.append("Use the following information to answer the question:\n")
        prompt_parts.append(f"{context_info.strip()}\n")
        
        # Include student context from intent gathering
        prompt_parts.append("The student's context based on our conversation:")
        prompt_parts.append(f"- What they already know: {known_information}")
        prompt_parts.append(f"- Why they're asking: {motivation}")
        prompt_parts.append(f"- What they want to learn: {learning_goal}\n")
        
        prompt_parts.append("Now, generate a response that does the following:\n")
    
        # Add intent-specific templates for substantive questions
        template = intent_prompt_templates.get(category, {}).get(specific_type)
        if template:
            prompt_parts.append(f"- {template}")
            
        # Add secondary intent handling if confidence is good
        secondary_intent = intent_data.get("intents", {}).get("secondary_intent", {})
        if secondary_intent and secondary_intent.get("confidence", 0.0) > 0.3:
            sec_category = secondary_intent.get("category", "")
            sec_type = secondary_intent.get("specific_type", "")
            sec_template = intent_prompt_templates.get(sec_category, {}).get(sec_type)
            if sec_template:
                prompt_parts.append(f"- Also: {sec_template}")
    
    # Handle conversational intents
    else:
        template = intent_prompt_templates.get(category, {}).get(specific_type)
        if template:
            prompt_parts.append(f"- {template}")
    
    # Universal instructions
    prompt_parts.append("\nImportant guidelines:")
    prompt_parts.append("- Frame the response in a friendly, conversational tone aimed at a curious student aged 10-12")
    prompt_parts.append("- Keep responses concise (max 4-5 sentences)")
    prompt_parts.append("- Always end with a question that encourages further engagement")
    prompt_parts.append("- If the input is unclear, guide them toward more meaningful topics rather than attempting to answer")
    
    return "\n".join(prompt_parts)

def generate_initial_response(query: str, intent_data: Optional[Dict[str, Any]], context_info: Optional[str] = None) -> Tuple[str, str]:
    """
    Generates the initial response based on the query, identified intents, and retrieved context.
    
    Args:
        query (str): The user's query
        intent_data (Optional[Dict[str, Any]]): The intent data from the intent gathering process
        context_info (Optional[str]): Retrieved context information about the topic
        
    Returns:
        Tuple[str, str]: The generated response and the prompt used to generate it
    """
    final_prompt = "" # Initialize
    try:
        logger.debug("Generating initial response prompt...")
        final_prompt = _generate_response_prompt(
            query, 
            intent_data if intent_data else {}, 
            context_info if context_info else ""
        )
        logger.debug(f"Generated initial response prompt: {final_prompt}")

        # Initialize LLM service
        logger.debug("Initializing LLM service for initial response generation")
        llm_service = LLMService()

        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": "You are Curiosity Coach, an educational AI designed to foster curiosity and engage students in meaningful learning conversations."},
            {"role": "user", "content": final_prompt}
        ]
        
        # Generate the initial response
        logger.debug("Generating initial response...")
        initial_response = llm_service.get_completion(messages, call_type="response_generation")

        logger.debug("Successfully generated initial response")
        return initial_response, final_prompt

    except Exception as e:
        error_msg = f"Failed to generate initial response: {str(e)}"
        if final_prompt:
            error_msg += f"\nPrompt used:\n{final_prompt}"
        logger.error(error_msg, exc_info=True)
        raise ResponseGenerationError(error_msg)