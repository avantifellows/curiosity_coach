import re
import json
from typing import List, Tuple, Dict, Any, Optional
from src.schemas import ConversationMemoryData, UserPersonaData


def _get_allowed_memory_keys() -> List[str]:
    try:
        # Use Pydantic model fields to derive keys dynamically
        return list(ConversationMemoryData.model_fields.keys())
    except Exception:
        # Safe fallback to current schema if import changes
        return ["curiosity_boosters", "invitation_to_come_back", "knowledge_journey", "kid_learning_profile"]

# Conversation memory placeholder regex
# Examples (all valid):
#   {{CONVERSATION_MEMORY}}
#   {{CONVERSATION_MEMORY__curiosity_boosters}}
#   {{CONVERSATION_MEMORY__knowledge_journey__initial_knowledge}}
#   Prefix/suffix in templates:
#     "Context: {{CONVERSATION_MEMORY}}" or "Context: {{CONVERSATION_MEMORY__curiosity_boosters}}"
PLACEHOLDER_REGEX = re.compile(r"\{\{CONVERSATION_MEMORY(?:__([A-Za-z0-9_]+(?:__[A-Za-z0-9_]+)*))?\}\}")

# Persona placeholder regex
# Examples (all valid):
#   {{USER_PERSONA}}
#   {{USER_PERSONA__persona}}
#   Prefix/suffix in templates:
#     "User: {{USER_PERSONA}}" or "User: {{USER_PERSONA__persona}}"
def _get_allowed_persona_keys() -> List[str]:
    try:
        return list(UserPersonaData.model_fields.keys())
    except Exception:
        return ["curiosity_boosters", "invitation_to_come_back", "knowledge_journey", "kid_learning_profile"]
PERSONA_PLACEHOLDER_REGEX = re.compile(r"\{\{USER_PERSONA(?:__([A-Za-z0-9_]+(?:__[A-Za-z0-9_]+)*))?\}\}")

# Previous conversations memory placeholder regex
# Example: {{PREVIOUS_CONVERSATIONS_MEMORY}}
PREVIOUS_MEMORY_PLACEHOLDER_REGEX = re.compile(
    r"\{\{PREVIOUS_CONVERSATIONS_MEMORY\}\}"
)


def extract_memory_placeholders(template: str) -> List[Tuple[str, List[str]]]:
    """
    Returns list of (full_token, requested_keys[]) pairs. requested_keys is empty for full injection.
    """
    results: List[Tuple[str, List[str]]] = []
    for match in PLACEHOLDER_REGEX.finditer(template):
        full_token = match.group(0)
        keys_blob = match.group(1)
        if keys_blob:
            # Split by '__' and validate simple tokens
            requested_keys = [part for part in keys_blob.split("__") if part]
        else:
            requested_keys = []
        results.append((full_token, requested_keys))
    return results


def _format_value_for_prompt(value: Any) -> str:
    if value is None:
        return "[Not available]"
    if isinstance(value, dict):
        # Convert nested dict to formatted JSON string
        try:
            return json.dumps(value, indent=2).replace('"', '\\"')
        except (TypeError, ValueError):
            return str(value).replace('"', '\\"')
    if isinstance(value, list):
        # Check if list contains dicts
        if value and isinstance(value[0], dict):
            try:
                return json.dumps(value, indent=2).replace('"', '\\"')
            except (TypeError, ValueError):
                pass
        joined = ", ".join([str(item) for item in value]) if value else "[Not available]"
        return joined.replace('"', '\\"')
    # Fallback to string
    return str(value).replace('"', '\\"') if value != "" else "[Not available]"


def render_memory_snippet(memory: Dict[str, Any], requested_keys: Optional[List[str]]) -> str:
    """
    Validates requested_keys against allowlist and renders a concise natural language snippet.
    If requested_keys is None or empty, include all allowed keys in a stable order.
    Invalid keys are omitted from rendering.
    Missing valid keys are rendered as [Not available].
    """
    keys_to_render: List[str]
    if not requested_keys:
        keys_to_render = _get_allowed_memory_keys()
    else:
        allowed = set(_get_allowed_memory_keys())
        keys_to_render = [k for k in requested_keys if k in allowed]

    parts: List[str] = []
    for key in keys_to_render:
        value = memory.get(key)
        value_str = _format_value_for_prompt(value)
        parts.append(f"`{key}` is \"{value_str}\"")

    if not parts:
        return "Conversation memory not available."

    return (
        "These are some details of the conversation till now. "
        + ", ".join(parts)
    )


def inject_memory_placeholders(template: str, memory: Optional[Dict[str, Any]]) -> str:
    """
    Replaces memory placeholders with a rendered snippet. If memory is None and placeholders
    exist, replaces them with a safe fallback message.
    """
    placeholders = extract_memory_placeholders(template)
    if not placeholders:
        return template

    if memory is None:
        fallback = "Conversation memory not available."
        for token, _ in placeholders:
            template = template.replace(token, fallback)
        return template

    # Replace each placeholder with appropriate rendering
    for token, requested_keys in placeholders:
        snippet = render_memory_snippet(memory, requested_keys if requested_keys else None)
        template = template.replace(token, snippet)

    return template


def extract_persona_placeholders(template: str) -> List[Tuple[str, List[str]]]:
    """
    Returns list of (full_token, requested_keys[]) pairs for persona placeholders.
    requested_keys is empty for full injection.
    """
    results: List[Tuple[str, List[str]]] = []
    for match in PERSONA_PLACEHOLDER_REGEX.finditer(template):
        full_token = match.group(0)
        keys_blob = match.group(1)
        if keys_blob:
            requested_keys = [part for part in keys_blob.split("__") if part]
        else:
            requested_keys = []
        results.append((full_token, requested_keys))
    return results


def render_persona_snippet(persona: Dict[str, Any], requested_keys: Optional[List[str]]) -> str:
    """
    Validates requested_keys against persona allowlist and renders concise snippet.
    If requested_keys is None or empty, include all allowed keys in stable order.
    Missing valid keys are rendered as [Not available].
    """
    keys_to_render: List[str]
    if not requested_keys:
        keys_to_render = _get_allowed_persona_keys()
    else:
        allowed = set(_get_allowed_persona_keys())
        keys_to_render = [k for k in requested_keys if k in allowed]

    parts: List[str] = []
    for key in keys_to_render:
        value = persona.get(key)
        value_str = _format_value_for_prompt(value)
        parts.append(f"`{key}` is \"{value_str}\"")

    if not parts:
        return "User persona not available."

    return (
        "These are some details about the user. "
        + ", ".join(parts)
    )


def inject_persona_placeholders(template: str, persona: Optional[Dict[str, Any]]) -> str:
    """
    Replaces {{USER_PERSONA}} placeholder with the complete persona JSON data.
    
    This provides the LLM with full access to the aggregated persona profile:
    - curiosity_boosters: What teaching techniques work best
    - invitation_to_come_back: Preferred conversation endings and return triggers
    - knowledge_journey: Primary interests and learning progression
    - kid_learning_profile: Overall learning style and engagement preferences
    
    Args:
        template: The prompt template with placeholders
        persona: Dictionary containing aggregated persona data
    
    Returns:
        Template with placeholder replaced with complete persona JSON
    """
    placeholders = extract_persona_placeholders(template)
    if not placeholders:
        return template

    if persona is None:
        fallback = "User persona not available yet (needs at least 3 completed conversations)."
        for token, _ in placeholders:
            template = template.replace(token, fallback)
        return template

    # Format: Simple header + complete JSON dump
    formatted = "=== USER PERSONA ===\n"
    formatted += "Aggregated learning profile based on all previous conversations with this student.\n"
    formatted += "Use this to personalize your teaching approach and build on what works.\n\n"
    formatted += json.dumps(persona, indent=2)
    
    for token, _ in placeholders:
        template = template.replace(token, formatted)

    return template


def inject_previous_memories_placeholder(
    template: str, 
    memories: Optional[List[Dict[str, Any]]]
) -> str:
    """
    Replace {{PREVIOUS_CONVERSATIONS_MEMORY}} with the complete raw memory JSON data.
    
    This provides the LLM with full access to all memory fields:
    - curiosity_boosters: What techniques worked/didn't work
    - invitation_to_come_back: How the conversation ended
    - knowledge_journey: What topics were explored
    - kid_learning_profile: How the kid learns best
    
    Args:
        template: The prompt template with placeholders
        memories: List of memory data dictionaries from previous conversations
    
    Returns:
        Template with placeholder replaced with complete memory JSON
    """
    if not PREVIOUS_MEMORY_PLACEHOLDER_REGEX.search(template):
        return template
    
    if not memories or len(memories) == 0:
        fallback = "No previous conversation memories available."
        return template.replace(
            "{{PREVIOUS_CONVERSATIONS_MEMORY}}", 
            fallback
        )
    
    # Format: Simple note + complete JSON dump of all memories
    formatted = "=== PREVIOUS CONVERSATION MEMORIES ===\n"
    formatted += "Below are complete memory analyses from previous conversations with this student.\n"
    formatted += "Use this data to build continuity, reference past topics, and adapt to their learning style.\n\n"
    
    for idx, memory in enumerate(memories, 1):
        formatted += f"--- Conversation {idx} ---\n"
        formatted += json.dumps(memory, indent=2)
        formatted += "\n\n"
    
    return template.replace(
        "{{PREVIOUS_CONVERSATIONS_MEMORY}}", 
        formatted.strip()
    )


