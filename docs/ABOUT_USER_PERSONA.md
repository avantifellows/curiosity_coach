# User Persona: Developer Guide

## What is a User Persona?

A user persona is a compact, structured summary of the user generated from their conversation memories. It helps the Brain tailor responses. The schema is validated in the Brain by `UserPersonaData`:

- `persona: string` (required)

## High-Level Flow

- Backend triggers persona generation (optionally refreshing missing/outdated conversation memories for that user first).
- Brain fetches the user's conversation memories, generates a persona with the LLM, validates it, and upserts via backend `/api/user-personas`.
- Brain can read the persona via an internal backend endpoint and inject it into prompts using placeholders.

## How to test the flow

**Option A: Using curl commands**

Set env vars for convenience:

```bash
export BACKEND="http://localhost:5000"
export USER_ID="1"            # Replace with your local user id
```

**Option B: Using OpenAPI documentation interface**

Navigate to `http://localhost:5000/api/docs` in your browser. You can search for "persona" or "generate-persona" to find the relevant endpoints and execute them directly from the interactive documentation.

1. Generate persona for a user

- Endpoint: POST `/api/tasks/generate-persona-for-user/{user_id}?generate_conversation_memories_if_not_found=true&only_needing=true&include_empty=false&clamp=-1&sync=true`
- Path params: `user_id` (int)
- Query: see above; `sync=true` recommended for local

```bash
curl -X POST "$BACKEND/api/tasks/generate-persona-for-user/$USER_ID?generate_conversation_memories_if_not_found=true&only_needing=true&include_empty=false&clamp=-1&sync=true"
```

2. Verify the persona for that user

- Endpoint: GET `/api/internal/users/{user_id}/persona`
- Note: Internal endpoint; no auth required for local testing

```bash
curl "$BACKEND/api/internal/users/$USER_ID/persona"
```

3. Add persona placeholder to your prompt and see it injected

Option A (local file, easiest): Edit `Brain/src/prompts/simplified_conversation_prompt.txt` to include a line like:

```text
User context: {{USER_PERSONA__persona}}
```

Option B (backend prompt versioning): Create a new active version for `simplified_conversation` containing the placeholder.

```bash
curl -X POST "$BACKEND/api/prompts/simplified_conversation/versions?set_active=true" \
  -H "Content-Type: application/json" \
  -d '{"prompt_text": "... User context: {{USER_PERSONA}} ..."}'
```

Now send a message and inspect the stored prompt to verify injection:

```bash
# Send a chat message (auth uses Bearer <user_id>)
CONVERSATION_ID=123  # replace
USER_MSG_ID=$(curl -s -X POST "$BACKEND/api/conversations/$CONVERSATION_ID/messages" \
  -H "Authorization: Bearer $USER_ID" -H "Content-Type: application/json" \
  -d '{"content":"Hello","purpose":"chat"}' | jq -r '.message.id')

# Poll for the AI response
AI_MSG_ID=$(curl -s "$BACKEND/api/messages/$USER_MSG_ID/response" \
  -H "Authorization: Bearer $USER_ID" | jq -r '.id')

# Fetch pipeline steps and inspect the 'prompt' field for the persona snippet
curl "$BACKEND/api/messages/$AI_MSG_ID/pipeline_steps" -H "Authorization: Bearer $USER_ID"
```

## Backend Components

- Models: `user_personas (id, user_id unique, persona_data, created_at, updated_at)`.
- Upsert endpoint: POST `/api/user-personas` with `{ user_id, persona_data }`.
- Task endpoints:
  - POST `/api/tasks/generate-persona-for-user/{user_id}` – options: `generate_conversation_memories_if_not_found`, `only_needing`, `include_empty`, `clamp`, `sync`.
  - Existing: `trigger-user-persona-generation` (global or a single `user_id`) async/sync variants.
- Internal read endpoint (Brain only):
  - GET `/api/internal/users/{user_id}/persona` – single user persona.

## Brain Components

- Persona generation handler: `core/user_persona_generator.py` – reads memories, prompts LLM, validates against `UserPersonaData`, upserts via backend.
- Prompt injection utilities: `src/utils/prompt_injection.py`
  - `extract_persona_placeholders(template)`
  - `render_persona_snippet(persona, requested_keys)`
  - `inject_persona_placeholders(template, persona)`
- Injection points:
  - Simplified mode: `process_query_entrypoint.generate_simplified_response(...)`
  - Full pipeline: `core/final_response_generator.generate_initial_response(...)`

## Placeholders: Usage and Behavior

- `{{USER_PERSONA}}` → injects all validated top-level keys per `UserPersonaData` (currently `persona`).
- `{{USER_PERSONA__persona}}` → inject only specified keys.
- Missing values render as `[Not available]`.

## Examples of Prompt Injection

Here are examples showing how persona placeholders are replaced with actual data:

### Example 1: Full Persona Injection

**Template:**
```
You are a curiosity coach. Tailor your response to this student.

User context: {{USER_PERSONA}}

Student question: Tell me about space exploration.
```

**Sample Persona Data:**
```json
{
  "persona": "The user has a strong interest in both natural sciences (physics of light) and history (Ancient Rome). They learn effectively through analogies and show a deep curiosity for engineering and technical details, as evidenced by their questions about aqueducts."
}
```

**After Injection:**
```
You are a curiosity coach. Tailor your response to this student.

User context: These are some details about the user. `persona` is "The user has a strong interest in both natural sciences (physics of light) and history (Ancient Rome). They learn effectively through analogies and show a deep curiosity for engineering and technical details, as evidenced by their questions about aqueducts."

Student question: Tell me about space exploration.
```

### Example 2: Specific Key Injection

**Template:**
```
Student profile: {{USER_PERSONA__persona}}

Based on their interests, answer their question about rockets.
```

**After Injection:**
```
Student profile: These are some details about the user. `persona` is "The user has a strong interest in both natural sciences (physics of light) and history (Ancient Rome). They learn effectively through analogies and show a deep curiosity for engineering and technical details, as evidenced by their questions about aqueducts."

Based on their interests, answer their question about rockets.
```

### Example 3: Invalid Keys and Missing Persona

**Template:**
```
User info: {{USER_PERSONA__invalid_key}}
Learning style: {{USER_PERSONA__persona}}
```

**With Invalid Key (ignored):**
```
User info: User persona not available.
Learning style: These are some details about the user. `persona` is "The user has a strong interest in both natural sciences (physics of light) and history (Ancient Rome). They learn effectively through analogies and show a deep curiosity for engineering and technical details, as evidenced by their questions about aqueducts."
```

**When No Persona Available:**
```
User info: User persona not available.
Learning style: User persona not available.
```

## Error Handling and Edge Cases

- Persona missing at injection time → token replaced with `User persona not available.`
- Validation failure when generating persona → persona is not saved; check logs.
- Long values: rendered as-is; consider truncation later if needed.

## Customizing Persona Generation

You can customize how user personas are generated by editing the persona generation prompt:

**File:** `Brain/src/prompts/user_persona_generation_prompt.txt`

This file contains the prompt template that instructs the LLM on how to analyze conversation memories and generate user personas. You can modify the instructions, output format requirements, or add additional guidance to better suit your use case.

## Testing Notes

- E2E tests can reuse memory flow setup; ensure persona is generated and injected into prompts.


