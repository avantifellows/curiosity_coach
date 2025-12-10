# Conversation Memory: Developer Guide

## What is Conversation Memory?

Conversation memory is a structured summary of a conversation that captures key topics, suggested actions, and a typical observation about the student. It enables the Brain to personalize responses by injecting salient details from prior exchanges into prompts.

Schema (Brain `ConversationMemoryData`):

- `main_topics: string[]`
- `action: string[]`
- `typical_observation: string`

## High-Level Flow

- Backend triggers memory generation tasks (batch or targeted).
- Brain fetches conversation history, generates structured memory with LLM, validates it, and upserts via backend `/api/memories`.
- Brain can read a conversation’s memory via an internal backend endpoint and inject it into prompts using placeholders.

## How to test the flow

**Option A: Using curl commands**

Set an environment variable for convenience:

```bash
export BACKEND="http://localhost:5000"
export USER_ID="1"            # Replace with your local user id
export CONVERSATION_ID="123"  # Replace with your conversation id
```

**Option B: Using OpenAPI documentation interface**

Navigate to `http://localhost:5000/api/docs` in your browser. You can search for "memory" or "generate-memory" to find the relevant endpoints and execute them directly from the interactive documentation.

1. Generate memory for a conversation

- Endpoint: POST `/api/tasks/generate-memory-for-conversation/{conversation_id}?sync=true`
- Path params: `conversation_id` (int)
- Query: `sync` (bool, optional; true recommended for local)

```bash
curl -X POST "$BACKEND/api/tasks/generate-memory-for-conversation/$CONVERSATION_ID?sync=true"
```

2. Verify the generated memory for that conversation

- Endpoint: GET `/api/internal/conversations/{conversation_id}/memory`
- Note: Internal endpoint; no auth required for local testing

```bash
curl "$BACKEND/api/internal/conversations/$CONVERSATION_ID/memory"
```

3. Add the memory placeholder to your main prompt and see it injected

Option A (local file, easiest): Edit `Brain/src/prompts/simplified_conversation_prompt.txt` to include a line like:

```text
Context: {{CONVERSATION_MEMORY__main_topics__action}}
```

Option B (backend prompt versioning): Create a new active version for `simplified_conversation` containing the placeholder.

```bash
curl -X POST "$BACKEND/api/prompts/simplified_conversation/versions?set_active=true" \
  -H "Content-Type: application/json" \
  -d '{"prompt_text": "... Context: {{CONVERSATION_MEMORY}} ..."}'
```

Now send a message and inspect the stored prompt to verify injection:

```bash
# Send a chat message to the conversation (auth uses Bearer <user_id>)
USER_MSG_ID=$(curl -s -X POST "$BACKEND/api/conversations/$CONVERSATION_ID/messages" \
  -H "Authorization: Bearer $USER_ID" -H "Content-Type: application/json" \
  -d '{"content":"Hello","purpose":"chat"}' | jq -r '.message.id')

# Poll for the AI response (returns the AI message when ready)
AI_MSG_ID=$(curl -s "$BACKEND/api/messages/$USER_MSG_ID/response" \
  -H "Authorization: Bearer $USER_ID" | jq -r '.id')

# Fetch pipeline steps and inspect the 'prompt' field for the memory snippet
curl "$BACKEND/api/messages/$AI_MSG_ID/pipeline_steps" -H "Authorization: Bearer $USER_ID"
```

## Backend Components

- Models: `conversation_memories (id, conversation_id unique, memory_data, created_at, updated_at)`.
- Upsert endpoint: POST `/api/memories` with `{ conversation_id, memory_data }`.
- Selection helpers:
  - `get_conversations_needing_memory(db)` – global selection using inactivity threshold and staleness.
  - `get_conversations_needing_memory_for_user(db, user_id, only_needing=True, include_empty=False)` – user-scoped variant.
- Task endpoints:
  - POST `/api/tasks/trigger-memory-generation` and `/sync` – existing global triggers.
  - POST `/api/tasks/generate-memory-for-conversation/{conversation_id}` – single conversation (supports `?sync=true`).
  - POST `/api/tasks/generate-memories-for-user/{user_id}` – filters: `only_needing`, `include_empty`, `clamp`, `sync`.
- Internal read endpoints (Brain only):
  - GET `/api/internal/conversations/{conversation_id}/messages_for_brain` – history for generation.
  - GET `/api/internal/users/{user_id}/memories` – all memories for persona generation.
  - GET `/api/internal/conversations/{conversation_id}/memory` – single conversation memory.

## Brain Components

- Task handler: POST `/tasks` with `task_type` `GENERATE_MEMORY_BATCH`.
- Generation pipeline:
  1) Fetch conversation history via internal endpoint.
  2) Format to LLM with `memory_generation_prompt.txt`.
  3) Parse, validate with `ConversationMemoryData`, and upsert via backend `/api/memories`.
- Memory retrieval for prompt injection:
  - `APIService.get_conversation_memory(conversation_id) -> Optional[Dict[str, Any]]` reads internal endpoint.
- Prompt injection utilities (`src/utils/prompt_injection.py`):
  - `extract_memory_placeholders(template)` → finds `{{CONVERSATION_MEMORY}}` and `{{CONVERSATION_MEMORY__key1__key2}}` tokens.
  - `render_memory_snippet(memory, requested_keys)` → validates keys, formats values, builds concise snippet.
  - `inject_memory_placeholders(template, memory)` → replaces tokens with snippet; uses fallback if memory is absent.
  - Allowed keys: `main_topics`, `action`, `typical_observation`.

## Where Injection Happens

- Simplified mode: `process_query_entrypoint.generate_simplified_response(...)` injects after loading the template and before LLM call.
- Full pipeline: `core/final_response_generator.generate_initial_response(...)` injects after formatting the prompt and before LLM call.
- Memory is fetched once per request in `src/main.py` and passed into processing functions.

## Placeholders: Usage and Behavior

- `{{CONVERSATION_MEMORY}}` → injects all allowed keys as: `These are some details of the conversation till now. \`key\` is "value", ...`.
- `{{CONVERSATION_MEMORY__main_topics__action}}` → injects only specified keys.
- Invalid keys are ignored; missing values render as `[Not available]`.
- Quotes are escaped to keep prompts safe.

## Examples of Prompt Injection

Here are examples showing how memory placeholders are replaced with actual data:

### Example 1: All Keys Injection

**Template:**
```
You are a curiosity coach. Help the student with their question.

Context: {{CONVERSATION_MEMORY}}

Student question: How do plants grow?
```

**Sample Memory Data:**
```json
{
  "main_topics": ["photosynthesis", "plant biology", "gardening"],
  "action": ["observe plants at home", "try growing seeds"],
  "typical_observation": "Shows curiosity about nature and enjoys hands-on learning"
}
```

**After Injection:**
```
You are a curiosity coach. Help the student with their question.

Context: These are some details of the conversation till now. `main_topics` is "photosynthesis, plant biology, gardening", `action` is "observe plants at home, try growing seeds", `typical_observation` is "Shows curiosity about nature and enjoys hands-on learning".

Student question: How do plants grow?
```

### Example 2: Specific Keys Injection

**Template:**
```
Previous topics discussed: {{CONVERSATION_MEMORY__main_topics}}
Suggested activities: {{CONVERSATION_MEMORY__action}}

Now answer the student's new question.
```

**After Injection:**
```
Previous topics discussed: These are some details of the conversation till now. `main_topics` is "photosynthesis, plant biology, gardening".
Suggested activities: These are some details of the conversation till now. `action` is "observe plants at home, try growing seeds".

Now answer the student's new question.
```

### Example 3: Invalid Keys and Missing Memory

**Template:**
```
Context: {{CONVERSATION_MEMORY__invalid_key__main_topics}}
Student info: {{CONVERSATION_MEMORY__typical_observation}}
```

**With Invalid Key (ignored):**
```
Context: These are some details of the conversation till now. `main_topics` is "photosynthesis, plant biology, gardening".
Student info: These are some details of the conversation till now. `typical_observation` is "Shows curiosity about nature and enjoys hands-on learning".
```

**When No Memory Available:**
```
Context: Conversation memory not available.
Student info: Conversation memory not available.
```

## Filters and Selection Logic

- `only_needing=true` uses inactivity threshold and stale-or-absent memory logic.
- `include_empty=false` excludes conversations with zero messages (heuristic: `updated_at > created_at`).
- `clamp` limits number of conversations in a request (`-1` for no limit).

## Local vs SQS Modes

- Backend `QueueService` decides between local HTTP (`LOCAL_BRAIN_ENDPOINT_URL` when `APP_ENV=development`) and SQS.
- `?sync=true` on single/user routes executes the enqueue path immediately in-process (local-oriented).

## Error Handling and Edge Cases

- No memory available during injection → token replaced with `Conversation memory not available.`
- Invalid keys in placeholder → ignored; snippet still renders with valid ones.
- Long content: The snippet is concise by design; truncation can be added if needed.
- Network failures to backend from Brain → memory fetch returns `None`; injection uses fallback.

## Testing Notes

- E2E tests include:
  - Memory upsert flow.
  - Global trigger.
  - Single conversation generation + internal memory read (status tolerant 200/404).
  - User-scoped generation with filters.

## How to Try It Locally

1) Run Backend and Brain with `./run.sh` in each service and set:
   - Backend: `.env.local` DB + `APP_ENV=development`, `LOCAL_BRAIN_ENDPOINT_URL=http://127.0.0.1:8001` (example).
   - Brain: `src/.env` with `BACKEND_CALLBACK_BASE_URL=http://127.0.0.1:5000`.
2) Create a conversation and a few messages.
3) Trigger a memory task:
   - Single: `POST /api/tasks/generate-memory-for-conversation/{conversation_id}?sync=true`.
   - User-scoped: `POST /api/tasks/generate-memories-for-user/{user_id}?only_needing=true&include_empty=false&clamp=10`.
4) Use a prompt that contains memory placeholders; verify injected text appears in stored pipeline prompt in callback payloads.

## Customizing Memory Generation

You can customize how conversation memories are generated by editing the memory generation prompt:

**File:** `Brain/src/prompts/memory_generation_prompt.txt`

This file contains the prompt template that instructs the LLM on how to analyze conversations and extract structured memory data. You can modify the instructions, output format requirements, or add additional guidance to better suit your use case.

## Future Enhancements (ideas)

- `{{CONVERSATION_MEMORY_JSON}}` to inject raw JSON.
- Configurable truncation for injected snippets.
- Extend allowlist with additional validated keys as schema evolves.
