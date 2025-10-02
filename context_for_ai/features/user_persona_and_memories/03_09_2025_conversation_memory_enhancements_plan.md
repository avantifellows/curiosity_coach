## Conversation Memory Enhancements: Implementation Plan and Task List

### Scope
- Add backend endpoints to generate/regenerate a memory for a specific conversation and for all conversations of a user.
- Enable prompt-time injection of a conversation’s memory in the Brain using flexible variables:
  - {{CONVERSATION_MEMORY}} → inject all top-level keys as a readable snippet
  - {{CONVERSATION_MEMORY__key1__key2}} → inject only the specified top-level keys, validated strictly

### Current State (baseline)
- Memory table exists: `conversation_memories` with one row per conversation (`id`, `conversation_id`, `memory_data`, `created_at`, `updated_at`).
- Brain can generate memories in batch via `/tasks` with `GENERATE_MEMORY_BATCH` and saves with backend `/api/memories` (upsert).
- Backend exposes task triggers for batch (all eligible conversations) but not for a single conversation nor user-scoped.
- Brain prompt templating supports `{{QUERY}}`, `{{CONVERSATION_HISTORY}}`, and optional `{{USER_PERSONA}}`; no memory injection yet.

---

## Design

### 1) Backend API

#### 1.a Generate/regenerate memory for a specific conversation
- Route: `POST /api/tasks/generate-memory-for-conversation/{conversation_id}` → 202
- Query params (optional):
  - `sync` (bool, default false): when true, run synchronously (local mode only) mirroring `trigger-memory-generation-sync` pattern.
- Behavior:
  - Validate conversation exists and has messages.
  - Call the existing queue path to the Brain (reuse `enqueue_memory_generation_task`) with a single-element list `[conversation_id]`.
  - Return 202 with message.

Notes: Brain’s memory save path is idempotent (upsert). This covers both generate and regenerate.

#### 1.b Generate memories for all conversations of a user
- Route: `POST /api/tasks/generate-memories-for-user/{user_id}` → 202
- Query params:
  - `only_needing` (bool, default true): if true, include only conversations needing (no memory yet OR memory older than conversation’s updated_at, same logic as `get_conversations_needing_memory`).
  - `include_empty` (bool, default false): if false, skip conversations with zero messages.
  - `clamp` (int, default -1): limit number of conversations in this request; -1 = no limit.
  - `sync` (bool, default false): run synchronously (local mode only).
- Behavior:
  - Query conversation IDs for the user, honoring `only_needing` and `include_empty`.
  - Enqueue `[conversation_ids...]` via the same queue path used today.
  - Return 202 with counts.

Implementation detail:
- Add a DB helper akin to `get_conversations_needing_memory_for_user(db, user_id)` to mirror the global helper but scoped to a user.

#### 1.c Internal read endpoint for a single conversation’s memory (used by Brain)
- Route: `GET /api/internal/conversations/{conversation_id}/memory` → 200 or 404
- Response body:
  - `MemoryInDB` (id, conversation_id, memory_data)

Reason: Brain needs a clean way to fetch the memory for the current conversation when injecting variables.

Security: Keep “internal” router excluded from public docs, as already done.

### 2) Brain: conversation memory prompt injection

Goal: Allow templates to include conversation memory with strict validation and flexible selection of keys.

#### 2.a Placeholder syntax
- `{{CONVERSATION_MEMORY}}`: inject all top-level keys from the memory JSON, rendered as a readable snippet.
- `{{CONVERSATION_MEMORY__key1__key2__...}}`: inject only the specified top-level keys in the same snippet.

Validation rules:
- Allowed top-level keys come from the Pydantic model `ConversationMemoryData` in `src/schemas.py`:
  - `main_topics: List[str]`
  - `action: List[str]`
  - `typical_observation: str`
- Any requested key not in this allowlist is considered invalid and must not be injected; log and omit (or replace with a clear token like `[Invalid key: X]`).
- If a valid key is missing in the actual memory data, inject `[Not available]`.

Render format (for either all keys or a specified set):
```
These are some details of the conversation till now. `key_name` is "value of the key", `key_name` is "value of the key" ...
```
Notes:
- For lists (e.g., `main_topics`, `action`), join as a natural-language string, e.g., `"Topic A, Topic B"`.
- Escape quotes in values to avoid template breakage.

#### 2.b Retrieval of conversation memory in Brain
- Add `APIService.get_conversation_memory(conversation_id: int) -> Optional[Dict[str, Any]]` calling:
  - `GET {BACKEND_CALLBACK_BASE_URL}/api/internal/conversations/{conversation_id}/memory`
  - Returns `.get("memory_data")` or `None` on 404.

#### 2.c Injection utility (shared)
- New module: `src/utils/prompt_injection.py`
  - `extract_memory_placeholders(template: str) -> List[Tuple[str, List[str]]]`
    - Returns pairs of (full_token, requested_keys[]) where `requested_keys` is empty for full injection or a list for specific keys.
  - `render_memory_snippet(memory: Dict[str, Any], requested_keys: Optional[List[str]]) -> str`
    - Validates requested keys against allowlist and renders per the rules.
  - `inject_memory_placeholders(template: str, memory: Optional[Dict[str, Any]]) -> str`
    - If `memory` is None and any placeholders exist, replace with a safe fallback like: `Conversation memory not available.`

#### 2.d Integration points
- In `src/main.py::dequeue()`:
  - If the prompt(s) to be used might contain memory placeholders, fetch memory once using `conversation_id` and cache for this request.
  - Pass `conversation_memory` to downstream prompt builders.

- Simplified mode:
  - In `process_query_entrypoint.generate_simplified_response(...)`:
    - After fetching the template (backend/FS) and before LLM call, call `inject_memory_placeholders`.

- Full pipeline:
  - In `core/final_response_generator.generate_initial_response(...)`:
    - Accept `conversation_memory: Optional[Dict[str, Any]]` and inject into the selected template before further replacements.
  - If other steps later adopt memory usage, they can call the same utility.

Compatibility:
- If no memory placeholders exist in a template, no extra work is done.
- If placeholders exist but no memory is available, a clear fallback is injected.

---

## API Details

### Backend

1) POST `/api/tasks/generate-memory-for-conversation/{conversation_id}`
- Response 202 `{ "message": "Queued memory generation for conversation_id X" }`
- Sync variant query `?sync=true` → returns 200 after completion (local development only).

2) POST `/api/tasks/generate-memories-for-user/{user_id}`
- Query params: `only_needing=true|false`, `include_empty=true|false`, `clamp=-1`, `sync=false|true`.
- Response 202 `{ "message": "Queued memory generation for N conversations (user Y)" }`.

3) GET `/api/internal/conversations/{conversation_id}/memory`
- 200 body: `{ id, conversation_id, memory_data }`
- 404 if none.

### Brain

1) GET conversation memory (internal API call)
- `api_service.get_conversation_memory(conversation_id)` → returns `memory_data` or `None`.

2) Prompt placeholders
- As specified in the design; validated keys only.

---

## Edge Cases & Error Handling
- Conversation exists but has no messages: skip unless `include_empty=true`.
- Memory already exists: regenerate will overwrite via upsert.
- Invalid keys in placeholder: omit from output and log (or inject `[Invalid key: X]`).
- Long values: truncate safely (e.g., first 500 chars) to avoid prompt bloat; configurable.
- Network failures to backend from Brain: inject fallback text and continue.

---

## Testing Plan
- Unit tests (Brain):
  - `extract_memory_placeholders` parses tokens correctly.
  - `render_memory_snippet` validates keys, formats lists/strings, escapes quotes.
  - `inject_memory_placeholders` handles none/missing/invalid keys.
- Unit tests (Backend):
  - User-scoped query returns correct conversation IDs for `only_needing` and `include_empty` permutations.
  - Single-conversation route validates existence and enqueues once.
  - Internal memory read returns 404/200 appropriately.
- E2E tests:
  - Create conversation with messages; trigger single-conversation memory generation; verify `conversation_memories` upserted.
  - Trigger for user; verify all selected conversations processed.
  - Use a prompt containing `{{CONVERSATION_MEMORY__main_topics}}` and verify the injected snippet is present in the stored pipeline step prompt (or in logs if exposed).

---

## Rollout & Backward Compatibility
- Non-breaking: new endpoints only; existing batch triggers unchanged.
- Prompt injection is additive; templates without memory placeholders are unaffected.
- Feature flags not required; behavior is template-driven.

---

## Implementation Tasks

### Backend
1. Add route: `POST /api/tasks/generate-memory-for-conversation/{conversation_id}` in `backend/src/tasks/router.py`.
2. Add route: `POST /api/tasks/generate-memories-for-user/{user_id}` in `backend/src/tasks/router.py`.
3. Add DB helper(s):
   - `get_conversations_needing_memory_for_user(db, user_id)` in `backend/src/models.py` (or a small CRUD helper).
   - Optional: `get_user_conversation_ids(db, user_id, include_empty)`.
4. Add internal route: `GET /api/internal/conversations/{conversation_id}/memory` in `backend/src/internal/router.py`.
5. Wire through `QueueService.enqueue_memory_generation_task` for both new routes; add `sync` variants similar to existing endpoints.
6. Tests: unit + E2E for routes and selection logic.

### Brain
7. Add `api_service.get_conversation_memory(conversation_id)`.
8. Implement `src/utils/prompt_injection.py` with extract/render/inject helpers.
9. In `src/main.py::dequeue()`, fetch memory when needed and pass to downstream (detect placeholders or add a small flag in FlowConfig to force-fetch). 
10. In `process_query_entrypoint.generate_simplified_response`, call `inject_memory_placeholders` before LLM call.
11. In `core/final_response_generator.generate_initial_response`, accept `conversation_memory` and inject into the selected template before other replacements.
12. Tests: unit tests for injection utilities; integration tests to ensure placeholders get replaced.

### Optional Enhancements
13. Allow `{{CONVERSATION_MEMORY_JSON}}` to inject the raw JSON (stringified) when needed.
14. Add max-length truncation config for injected snippets.

---

## Acceptance Criteria
- Backend:
  - Can enqueue memory generation for a specific conversation by id; regenerates if existing.
  - Can enqueue memory generation for all conversations of a user with filters.
  - Brain can read a single conversation’s memory via internal endpoint.
- Brain:
  - Templates with `{{CONVERSATION_MEMORY}}` inject all validated keys or fallback text if missing.
  - Templates with `{{CONVERSATION_MEMORY__key1__key2}}` inject only requested, validated keys.
  - Invalid keys are safely handled and logged.


