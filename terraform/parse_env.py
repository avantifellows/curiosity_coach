import sys
import json
import os
from pathlib import Path

def parse_dotenv(dotenv_path):
    """Parses a .env file and returns a dictionary of key-value pairs."""
    env_vars = {}
    # Resolve the absolute path to handle different execution contexts
    absolute_dotenv_path = Path(dotenv_path).resolve()

    if not absolute_dotenv_path.is_file():
        # Log to stderr if file not found, return empty dict
        print(f"Error: dotenv file not found at {absolute_dotenv_path}", file=sys.stderr)
        return {}

    try:
        with open(absolute_dotenv_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Find the first '=' sign
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Basic handling for quotes (remove if present at ends)
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    # Handle potential escaped characters (basic example)
                    value = value.replace('\\$', '$') # Unescape dollar sign
                    env_vars[key] = value
    except Exception as e:
        print(f"Error parsing dotenv file {absolute_dotenv_path}: {e}", file=sys.stderr)
        return {} # Return empty on error
    return env_vars

if __name__ == "__main__":
    try:
        # Read input JSON from stdin (passed by Terraform data source)
        # Expects input like: {"dotenv_path": "../.env.prod"}
        input_data = json.load(sys.stdin)
        dotenv_file_path_input = input_data.get('dotenv_path')

        if not dotenv_file_path_input:
            print("Error: 'dotenv_path' not provided in input JSON", file=sys.stderr)
            print(json.dumps({})) # Output empty JSON to stdout
            sys.exit(1)

        # The script's working directory is the terraform directory
        # So the path should be relative to that, or absolute.
        # Let's assume the path passed is relative to the terraform directory.
        env_variables = parse_dotenv(dotenv_file_path_input)

        # Output the parsed variables as JSON to stdout
        print(json.dumps(env_variables))

    except Exception as e:
        print(f"Script Error: {e}", file=sys.stderr)
        print(json.dumps({})) # Output empty JSON on script error
        sys.exit(1) 