"""
Utility to parse JSON schemas from prompt files.

This module extracts the expected JSON output structure from prompt templates
that define output formats for LLMs. It searches for JSON examples in prompts
and parses them to understand the nested structure of fields.
"""

import re
import json
from typing import Dict, Any, List, Optional
from pathlib import Path


def extract_json_from_prompt(prompt_content: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON structure from a prompt file.

    Looks for JSON blocks in the prompt (within ``` markers or raw JSON).
    Returns the parsed structure or None if not found.

    Args:
        prompt_content: The full text content of the prompt file

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


def parse_prompt_file(prompt_path: str) -> Optional[Dict[str, Any]]:
    """
    Parse a prompt file and extract its JSON schema.

    Args:
        prompt_path: Path to the prompt text file

    Returns:
        Dictionary with schema info:
        {
            "raw_json": {...},  # The example JSON found
            "schema": {...},     # Structured schema with types
            "fields": [...]      # Flat list of all fields
        }
    """
    try:
        with open(prompt_path, 'r') as f:
            content = f.read()

        raw_json = extract_json_from_prompt(content)
        if not raw_json:
            return None

        schema = build_field_schema(raw_json)
        fields = generate_field_list(schema)

        return {
            "raw_json": raw_json,
            "schema": schema,
            "fields": fields
        }

    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error parsing prompt file {prompt_path}: {e}")
        return None


# Hardcoded mapping of placeholder variables to their source prompt files
VARIABLE_TO_PROMPT_MAPPING = {
    "USER_PERSONA": "Brain/src/prompts/user_persona_generation_prompt.txt",
    "PREVIOUS_CONVERSATIONS_MEMORY": "Brain/src/prompts/memory_generation_prompt.txt",
}


def get_placeholder_schema(variable_name: str, project_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get the schema for a specific placeholder variable.

    Args:
        variable_name: One of "USER_PERSONA", "PREVIOUS_CONVERSATIONS_MEMORY"
        project_root: Root directory of the project (optional, will try to infer)

    Returns:
        Schema dictionary or None if not found
    """
    if variable_name not in VARIABLE_TO_PROMPT_MAPPING:
        return None

    prompt_path = VARIABLE_TO_PROMPT_MAPPING[variable_name]

    # If project_root provided, make it absolute
    if project_root:
        full_path = Path(project_root) / prompt_path
    else:
        # Try to find the file relative to this script
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent  # Go up to project root
        full_path = project_root / prompt_path

    return parse_prompt_file(str(full_path))


def generate_ui_metadata(project_root: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate metadata for all placeholder variables for UI consumption.

    Args:
        project_root: Root directory of the project

    Returns:
        Dictionary mapping variable names to their schemas and field lists:
        {
            "USER_PERSONA": {
                "source_file": "...",
                "schema": {...},
                "fields": [...]
            },
            ...
        }
    """
    metadata = {}

    for variable_name, prompt_path in VARIABLE_TO_PROMPT_MAPPING.items():
        schema_data = get_placeholder_schema(variable_name, project_root)

        if schema_data:
            metadata[variable_name] = {
                "source_file": prompt_path,
                "schema": schema_data["schema"],
                "fields": schema_data["fields"]
            }
        else:
            metadata[variable_name] = {
                "source_file": prompt_path,
                "error": "Could not parse schema from prompt file"
            }

    # Add special handling for PREVIOUS_CONVERSATIONS_MEMORY
    if "PREVIOUS_CONVERSATIONS_MEMORY" in metadata:
        metadata["PREVIOUS_CONVERSATIONS_MEMORY"]["is_array"] = True
        metadata["PREVIOUS_CONVERSATIONS_MEMORY"]["requires_runtime_index"] = True
        metadata["PREVIOUS_CONVERSATIONS_MEMORY"]["note"] = (
            "Array of conversation memories. User must specify index at runtime. "
            "Examples: {{PREVIOUS_CONVERSATIONS_MEMORY__0__curiosity_boosters}} for first conversation, "
            "or {{PREVIOUS_CONVERSATIONS_MEMORY__curiosity_boosters}} to get field from ALL conversations"
        )
        metadata["PREVIOUS_CONVERSATIONS_MEMORY"]["usage_patterns"] = [
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

    return metadata


if __name__ == "__main__":
    # Test the parser
    import sys
    import os

    # Get project root (assuming this script is in Brain/src/utils/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent

    print("=== Testing Prompt Schema Parser ===\n")

    # Generate metadata
    metadata = generate_ui_metadata(str(project_root))

    # Print results
    for variable_name, data in metadata.items():
        print(f"\n{'='*60}")
        print(f"Variable: {variable_name}")
        print(f"Source: {data.get('source_file')}")

        if "error" in data:
            print(f"Error: {data['error']}")
            continue

        if "is_array" in data:
            print(f"Note: {data['note']}")

        print(f"\nAvailable fields ({len(data.get('fields', []))}):")
        for field in data.get("fields", [])[:10]:  # Show first 10
            print(f"  - {field['path']} ({field['type']})")
            print(f"    Label: {field['label']}")

        if len(data.get("fields", [])) > 10:
            print(f"  ... and {len(data['fields']) - 10} more")

    # Export to JSON file for UI consumption (two locations)
    # 1. Brain utils folder (for reference)
    output_path_brain = project_root / "Brain" / "src" / "utils" / "placeholder_metadata.json"
    with open(output_path_brain, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"\n✅ Metadata exported to: {output_path_brain}")

    # 2. Frontend public folder (for runtime use)
    output_path_frontend = project_root / "curiosity-coach-frontend" / "public" / "placeholder_metadata.json"
    output_path_frontend.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path_frontend, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✅ Metadata exported to: {output_path_frontend}")
