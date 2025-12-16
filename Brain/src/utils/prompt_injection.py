import re
import json
from typing import List, Tuple, Dict, Any, Optional
from src.schemas import ConversationMemoryData, UserPersonaData


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
        # Fallback to schema fields if UserPersonaData import fails
        return ["what_works", "what_doesnt_work", "interests", "learning_style", "engagement_triggers", "red_flags"]
PERSONA_PLACEHOLDER_REGEX = re.compile(r"\{\{USER_PERSONA(?:__([A-Za-z0-9_]+(?:__[A-Za-z0-9_]+)*))?\}\}")

# Previous conversations memory placeholder regex
# Examples (all valid):
#   {{PREVIOUS_CONVERSATIONS_MEMORY}}
#   {{PREVIOUS_CONVERSATIONS_MEMORY__curiosity_boosters}}
#   {{PREVIOUS_CONVERSATIONS_MEMORY__0__curiosity_boosters}}  (access first conversation)
#   {{PREVIOUS_CONVERSATIONS_MEMORY__knowledge_journey__initial_knowledge}}
PREVIOUS_MEMORY_PLACEHOLDER_REGEX = re.compile(
    r"\{\{PREVIOUS_CONVERSATIONS_MEMORY(?:__([A-Za-z0-9_]+(?:__[A-Za-z0-9_]+)*))?\}\}"
)

# Core theme placeholder regex
# Examples (all valid):
#   {{CORE_THEME}}
CORE_THEME_PLACEHOLDER_REGEX = re.compile(r'\{\{CORE_THEME(?:\|([^}]+))?\}\}')

def extract_core_theme_placeholders(template: str) -> List[Tuple[str, List[str]]]:
    """
    Returns list of (full_token, requested_keys[]) pairs for core theme placeholders.
    """
    results: List[Tuple[str, List[str]]] = []
    for match in CORE_THEME_PLACEHOLDER_REGEX.finditer(template):
        full_token = match.group(0)
        keys_blob = match.group(1)
        if keys_blob:
            requested_keys = [part for part in keys_blob.split('|') if part]
        else:
            requested_keys = []
        results.append((full_token, requested_keys))
    return results

def inject_core_theme_placeholder(template: str, core_theme: Optional[str]) -> str:
    """
    Replaces {{CORE_THEME}} placeholders with core theme data.
    
    Args:
        template: The prompt template with placeholders
        core_theme: The extracted core theme string or None
        
    Returns:
        Template with placeholders replaced with core theme data
    """
    placeholders = extract_core_theme_placeholders(template)
    if not placeholders:
        return template

    if core_theme is None:
        fallback = "No current theme as such"
        for token, _ in placeholders:
            template = template.replace(token, fallback)
        return template

    # Replace each placeholder with the core theme
    for token, _ in placeholders:
        template = template.replace(token, core_theme)
    
    return template



def _get_nested_value(data: Dict[str, Any], key_path: List[str]) -> Any:
    """
    Traverse nested dictionary using key path.

    Args:
        data: The dictionary to traverse
        key_path: List of keys representing the path (e.g., ['curiosity_boosters', 'comment'])

    Returns:
        The value at the nested path, or None if not found

    Example:
        _get_nested_value({'a': {'b': 'value'}}, ['a', 'b']) -> 'value'
    """
    value = data
    for key in key_path:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return None
        elif isinstance(value, list):
            # Handle array access like ['key', '0', 'subkey']
            try:
                index = int(key)
                if 0 <= index < len(value):
                    value = value[index]
                else:
                    return None
            except (ValueError, TypeError):
                return None
        else:
            return None
    return value


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

    Supports nested key paths:
    - Single key: ['curiosity_boosters'] -> persona['curiosity_boosters']
    - Nested key: ['kid_learning_profile', 'attention_span', 'overall_assessment']
                  -> persona['kid_learning_profile']['attention_span']['overall_assessment']
    """
    if not requested_keys:
        # Full injection mode - render all allowed top-level keys
        keys_to_render = _get_allowed_persona_keys()
        parts: List[str] = []
        for key in keys_to_render:
            value = persona.get(key)
            value_str = _format_value_for_prompt(value)
            parts.append(f"`{key}` is \"{value_str}\"")
    else:
        # Nested path mode - requested_keys is a single path like ['kid_learning_profile', 'attention_span']
        # Validate that the first key is allowed
        allowed = set(_get_allowed_persona_keys())
        if requested_keys[0] not in allowed:
            return "User persona not available."

        # Get the nested value
        value = _get_nested_value(persona, requested_keys)
        value_str = _format_value_for_prompt(value)

        # Create a readable path for the label
        path_label = '__'.join(requested_keys)
        parts = [f"`{path_label}` is \"{value_str}\""]

    if not parts:
        return "User persona not available."

    return (
        "These are some details about the user. "
        + ", ".join(parts)
    )


def inject_persona_placeholders(template: str, persona: Optional[Dict[str, Any]]) -> str:
    """
    Replaces {{USER_PERSONA}} placeholders with persona data.

    Supports two modes:
    1. Full injection: {{USER_PERSONA}} -> Complete JSON dump of all persona data
    2. Selective injection: {{USER_PERSONA__what_works}} -> Only specific fields

    This provides the LLM with access to the aggregated persona profile:
    - what_works: Teaching techniques that resonate with this student
    - what_doesnt_work: Approaches that cause disengagement
    - interests: Main topics they're curious about
    - learning_style: How they prefer to learn
    - engagement_triggers: What gets them excited
    - red_flags: What causes them to lose interest

    Args:
        template: The prompt template with placeholders
        persona: Dictionary containing aggregated persona data

    Returns:
        Template with placeholders replaced with persona data
    """
    placeholders = extract_persona_placeholders(template)
    if not placeholders:
        return template

    if persona is None:
        fallback = "User persona not available yet (needs at least 3 completed conversations)."
        for token, _ in placeholders:
            template = template.replace(token, fallback)
        return template

    # Replace each placeholder based on whether keys were specified
    for token, requested_keys in placeholders:
        if not requested_keys:
            # Full injection mode - dump entire JSON
            formatted = "=== USER PERSONA ===\n"
            formatted += "Aggregated learning profile based on all previous conversations with this student.\n"
            formatted += "Use this to personalize your teaching approach and build on what works.\n\n"
            formatted += json.dumps(persona, indent=2)
            template = template.replace(token, formatted)
        else:
            # Selective injection mode - render only requested fields
            snippet = render_persona_snippet(persona, requested_keys)
            template = template.replace(token, snippet)

    return template


def extract_previous_memory_placeholders(template: str) -> List[Tuple[str, List[str]]]:
    """
    Returns list of (full_token, requested_keys[]) pairs for previous memory placeholders.
    requested_keys is empty for full injection.

    Examples:
    - {{PREVIOUS_CONVERSATIONS_MEMORY}} -> ('{{PREVIOUS_CONVERSATIONS_MEMORY}}', [])
    - {{PREVIOUS_CONVERSATIONS_MEMORY__curiosity_boosters}} -> (..., ['curiosity_boosters'])
    - {{PREVIOUS_CONVERSATIONS_MEMORY__0__curiosity_boosters}} -> (..., ['0', 'curiosity_boosters'])
    """
    results: List[Tuple[str, List[str]]] = []
    for match in PREVIOUS_MEMORY_PLACEHOLDER_REGEX.finditer(template):
        full_token = match.group(0)
        keys_blob = match.group(1)
        if keys_blob:
            requested_keys = [part for part in keys_blob.split("__") if part]
        else:
            requested_keys = []
        results.append((full_token, requested_keys))
    return results


def render_previous_memories_snippet(
    memories: List[Dict[str, Any]],
    requested_keys: Optional[List[str]]
) -> str:
    """
    Renders previous conversation memories based on requested keys.

    Supports:
    - Full dump: requested_keys = None or []
    - Specific field across all: ['curiosity_boosters']
    - Specific conversation: ['0', 'curiosity_boosters']
    - Nested paths: ['0', 'curiosity_boosters', 'comment']
    """
    if not requested_keys:
        # Full dump mode
        formatted = "=== PREVIOUS CONVERSATION MEMORIES ===\n"
        formatted += "Below are complete memory analyses from previous conversations with this student.\n"
        formatted += "Use this data to build continuity, reference past topics, and adapt to their learning style.\n\n"

        for idx, memory in enumerate(memories, 1):
            formatted += f"--- Conversation {idx} ---\n"
            formatted += json.dumps(memory, indent=2)
            formatted += "\n\n"

        return formatted.strip()

    # Check if first key is a number (specific conversation index)
    try:
        conv_index = int(requested_keys[0])
        # Access specific conversation
        if 0 <= conv_index < len(memories):
            memory = memories[conv_index]
            remaining_keys = requested_keys[1:]

            if not remaining_keys:
                # Just the conversation index, return full memory
                formatted = f"=== CONVERSATION {conv_index + 1} MEMORY ===\n"
                formatted += json.dumps(memory, indent=2)
                return formatted
            else:
                # Nested access into specific conversation
                value = _get_nested_value(memory, remaining_keys)
                value_str = _format_value_for_prompt(value)
                key_path = '__'.join(remaining_keys)
                return f"From conversation {conv_index + 1}, `{key_path}` is \"{value_str}\""
        else:
            return f"[Conversation index {conv_index} out of range (have {len(memories)} conversations)]"
    except (ValueError, TypeError):
        # Not a number - treat as field name across all conversations
        # Extract this field from all conversations
        parts = []
        for idx, memory in enumerate(memories, 1):
            value = _get_nested_value(memory, requested_keys)
            value_str = _format_value_for_prompt(value)
            key_path = '__'.join(requested_keys)
            parts.append(f"Conversation {idx}: `{key_path}` is \"{value_str}\"")

        return "Previous conversations data:\n" + "\n".join(parts)


def inject_previous_memories_placeholder(
    template: str,
    memories: Optional[List[Dict[str, Any]]]
) -> str:
    """
    Replace {{PREVIOUS_CONVERSATIONS_MEMORY}} placeholders with memory data.

    Supports multiple modes:
    1. Full injection: {{PREVIOUS_CONVERSATIONS_MEMORY}} -> All memories as JSON
    2. Field across all: {{PREVIOUS_CONVERSATIONS_MEMORY__curiosity_boosters}} -> Field from all conversations
    3. Specific conversation: {{PREVIOUS_CONVERSATIONS_MEMORY__0__curiosity_boosters}} -> Field from conv #1
    4. Nested paths: {{PREVIOUS_CONVERSATIONS_MEMORY__0__curiosity_boosters__comment}}

    This provides the LLM with access to memory fields:
    - curiosity_boosters: What techniques worked/didn't work
    - invitation_to_come_back: How the conversation ended
    - knowledge_journey: What topics were explored
    - kid_learning_profile: How the kid learns best

    Args:
        template: The prompt template with placeholders
        memories: List of memory data dictionaries from previous conversations

    Returns:
        Template with placeholders replaced with memory data
    """
    placeholders = extract_previous_memory_placeholders(template)
    if not placeholders:
        return template

    if not memories or len(memories) == 0:
        fallback = "No previous conversation memories available."
        for token, _ in placeholders:
            template = template.replace(token, fallback)
        return template

    # Replace each placeholder based on requested keys
    for token, requested_keys in placeholders:
        snippet = render_previous_memories_snippet(
            memories,
            requested_keys if requested_keys else None
        )
        template = template.replace(token, snippet)

    return template


