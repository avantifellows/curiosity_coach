"""
Utility to parse JSON schemas from prompt text for placeholder field extraction.

This module extracts the expected JSON output structure from prompt text
that defines output formats for LLMs. Used to dynamically generate UI metadata
for placeholder field selection in the prompt editor.
"""

import re
import json
from typing import Dict, Any, List, Optional


def extract_json_from_prompt(prompt_content: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON structure from a prompt text.

    Looks for JSON blocks in the prompt (within ``` markers or raw JSON).
    Returns the parsed structure or None if not found.

    Args:
        prompt_content: The full text content of the prompt

    Returns:
        Parsed JSON structure as a dictionary, or None if no valid JSON found
    """
    # Try to find JSON within code blocks first (```json or ```)
    code_block_pattern = r'```(?:json)?\s*\n(.*?)\n```'
    matches = re.findall(code_block_pattern, prompt_content, re.DOTALL)

    for match in matches:
        # Clean up common template syntax that might be in examples
        cleaned = match.replace('{{', '{').replace('}}', '}')
        # Remove comments (lines starting with //)
        cleaned = re.sub(r'//.*$', '', cleaned, flags=re.MULTILINE)
        # Fix common non-JSON patterns in prompts
        cleaned = re.sub(r':\s*true/false', ': true', cleaned)  # true/false -> true
        cleaned = re.sub(r'"[^"]*\s+/\s+[^"]*"', '"example"', cleaned)  # "a / b / c" -> "example"

        try:
            # Try to parse as JSON
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    # Try to find raw JSON (looking for objects starting with { and ending with })
    # Look for multi-line objects
    json_pattern = r'\{(?:[^{}]|\{[^{}]*\})*\}'
    matches = re.findall(json_pattern, prompt_content, re.DOTALL)

    for match in matches:
        # Clean template syntax
        cleaned = match.replace('{{', '{').replace('}}', '}')
        cleaned = re.sub(r'//.*$', '', cleaned, flags=re.MULTILINE)

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and len(parsed) > 2:  # Likely a schema, not just {}
                return parsed
        except json.JSONDecodeError:
            continue

    return None


def infer_field_type(value: Any) -> str:
    """
    Infer the type of a field from its example value.

    Args:
        value: The example value from the JSON

    Returns:
        Type string: "string", "number", "boolean", "array", "object", "null"
    """
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, (int, float)):
        return "number"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    else:
        return "unknown"


def build_field_schema(data: Any, path: str = "") -> Dict[str, Any]:
    """
    Recursively build a schema tree from example JSON data.

    Args:
        data: The data to analyze (can be dict, list, or primitive)
        path: Current path in the schema (for tracking depth)

    Returns:
        Schema dictionary with type info and nested fields
    """
    field_type = infer_field_type(data)

    schema = {
        "type": field_type,
        "path": path
    }

    if field_type == "object" and isinstance(data, dict):
        nested = {}
        for key, value in data.items():
            nested_path = f"{path}__{key}" if path else key
            nested[key] = build_field_schema(value, nested_path)
        schema["fields"] = nested

    elif field_type == "array" and isinstance(data, list):
        if len(data) > 0:
            # Analyze first item as representative
            item_schema = build_field_schema(data[0], f"{path}__0")
            schema["item_type"] = item_schema

    return schema


def generate_field_list(schema: Dict[str, Any], parent_path: str = "") -> List[Dict[str, str]]:
    """
    Generate a flat list of all fields with their full paths.

    This is useful for UI dropdown generation.

    Args:
        schema: The schema dictionary from build_field_schema
        parent_path: Parent path for recursion

    Returns:
        List of dicts with 'path', 'type', and 'label' keys

    Example:
        [
            {"path": "curiosity_boosters", "type": "object", "label": "curiosity_boosters"},
            {"path": "curiosity_boosters__comment", "type": "string", "label": "curiosity_boosters → comment"},
            ...
        ]
    """
    fields = []
    field_type = schema.get("type")
    current_path = schema.get("path", parent_path)

    # Add current field
    if current_path:
        label = current_path.replace("__", " → ")
        fields.append({
            "path": current_path,
            "type": field_type,
            "label": label
        })

    # Recurse into nested fields
    if field_type == "object" and "fields" in schema:
        for key, nested_schema in schema["fields"].items():
            nested_fields = generate_field_list(nested_schema, current_path)
            fields.extend(nested_fields)

    elif field_type == "array" and "item_type" in schema:
        # For arrays, show the item structure
        item_schema = schema["item_type"]
        if item_schema.get("type") == "object":
            # Add array items as accessible paths
            nested_fields = generate_field_list(item_schema, current_path)
            fields.extend(nested_fields)

    return fields


def parse_prompt_text(prompt_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse a prompt text and extract its JSON schema.

    Args:
        prompt_text: The prompt text content

    Returns:
        Dictionary with schema info:
        {
            "raw_json": {...},  # The example JSON found
            "schema": {...},     # Structured schema with types
            "fields": [...]      # Flat list of all fields
        }
    """
    try:
        raw_json = extract_json_from_prompt(prompt_text)
        if not raw_json:
            return None

        schema = build_field_schema(raw_json)
        fields = generate_field_list(schema)

        return {
            "raw_json": raw_json,
            "schema": schema,
            "fields": fields
        }

    except Exception as e:
        print(f"Error parsing prompt text: {e}")
        return None


# Hardcoded mapping of placeholder variables to their types
PLACEHOLDER_VARIABLE_INFO = {
    "CONVERSATION_MEMORY": {
        "description": "Memory data from the current conversation",
        "source": "memory_generation_prompt",
        "is_array": False
    },
    "USER_PERSONA": {
        "description": "Aggregated user persona from all conversations",
        "source": "user_persona_generation_prompt",
        "is_array": False
    },
    "PREVIOUS_CONVERSATIONS_MEMORY": {
        "description": "Memory data from previous conversations (array)",
        "source": "memory_generation_prompt",  # Same as CONVERSATION_MEMORY
        "is_array": True,
        "requires_runtime_index": True,
        "usage_patterns": [
            {
                "pattern": "{{PREVIOUS_CONVERSATIONS_MEMORY}}",
                "description": "Full dump of all previous conversation memories"
            },
            {
                "pattern": "{{PREVIOUS_CONVERSATIONS_MEMORY__<INDEX>}}",
                "description": "Full memory from conversation at INDEX (0-based). Example: {{PREVIOUS_CONVERSATIONS_MEMORY__0}}"
            },
            {
                "pattern": "{{PREVIOUS_CONVERSATIONS_MEMORY__<INDEX>__<FIELD>}}",
                "description": "Specific field from conversation at INDEX. Example: {{PREVIOUS_CONVERSATIONS_MEMORY__0__curiosity_boosters}}"
            },
            {
                "pattern": "{{PREVIOUS_CONVERSATIONS_MEMORY__<FIELD>}}",
                "description": "Same field from ALL conversations. Example: {{PREVIOUS_CONVERSATIONS_MEMORY__curiosity_boosters}}"
            }
        ]
    }
}


def get_placeholder_metadata_for_prompt(
    prompt_name: str,
    prompt_text: str,
    variable_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get metadata for placeholders based on a prompt's text.

    Args:
        prompt_name: Name of the prompt (e.g., "memory_generation_prompt")
        prompt_text: The actual prompt text content
        variable_name: Optional - the variable name to return metadata for

    Returns:
        Dictionary with metadata for all applicable variables or just the requested one
    """
    # Parse the prompt text
    parsed = parse_prompt_text(prompt_text)

    if not parsed:
        return {"error": "Could not extract JSON schema from prompt text"}

    # Find which variables use this prompt
    applicable_variables = []
    for var_name, var_info in PLACEHOLDER_VARIABLE_INFO.items():
        if var_info["source"] == prompt_name:
            applicable_variables.append(var_name)

    # Build metadata for each applicable variable
    metadata = {}
    for var_name in applicable_variables:
        var_info = PLACEHOLDER_VARIABLE_INFO[var_name]

        var_metadata = {
            "variable_name": var_name,
            "description": var_info["description"],
            "source_prompt": prompt_name,
            "is_array": var_info.get("is_array", False),
            "schema": parsed["schema"],
            "fields": parsed["fields"]
        }

        # Add special handling
        if var_info.get("requires_runtime_index"):
            var_metadata["requires_runtime_index"] = True
            var_metadata["usage_patterns"] = var_info["usage_patterns"]

        metadata[var_name] = var_metadata

    # If specific variable requested, return just that one
    if variable_name and variable_name in metadata:
        return metadata[variable_name]

    return metadata
