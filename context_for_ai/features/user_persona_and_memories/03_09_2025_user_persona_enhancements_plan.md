## User Persona Enhancements: Implementation Plan and Task List

### Scope
- Add a backend endpoint to generate/regenerate a persona for a specific user by `user_id` with an option to pre-generate any missing or outdated conversation memories for that user.
- Provide prompt-time injection for user persona in the Brain, mirroring conversation memory injection semantics:
  - `{{USER_PERSONA}}` → injects all allowed top-level keys as a concise snippet
  - `{{USER_PERSONA__key1__key2}}` → injects only the specified keys (validated strictly)

### Current State (baseline)
- Backend already supports persona generation triggers:
  - `POST /api/tasks/trigger-user-persona-generation` and `POST /api/tasks/trigger-user-persona-generation-sync` with optional `user_id` (queues `USER_PERSONA_GENERATION` via `QueueService`).
- Backend has memory-generation routes used by Brain and ops:
  - `POST /api/tasks/generate-memory-for-conversation/{conversation_id}`
  - `POST /api/tasks/generate-memories-for-user/{user_id}` with filters `only_needing`, `include_empty`, `clamp`, `sync`.
- Backend CRUD for persona save exists: `POST /api/user-personas`.
- Backend internal persona read endpoint is missing (Brain expects `GET /api/internal/users/{user_id}/persona`).
- Brain fetches persona via `api_service.get_user_persona(user_id)` (assumes internal endpoint), and simplified prompt supports only a basic `{{USER_PERSONA}}` replacement (JSON string). No selective-key injection yet.

---

## Design

### 1) Backend API

#### 1.a Generate/regenerate persona for a specific user (with optional memory refresh)
- Route: `POST /api/tasks/generate-persona-for-user/{user_id}` → 202 (or 200 when `sync=true`)
- Query params:
  - `generate_conversation_memories_if_not_found` (bool, default `true`): If true, compute conversations that either have no memory or have memories older than the conversation’s latest `updated_at`, and enqueue memory generation for those first.
  - `only_needing` (bool, default `true`): Passed to the memory selection when refreshing memories.
  - `include_empty` (bool, default `false`): Include conversations with zero messages when refreshing memories.
  - `clamp` (int, default `-1`): Limit the number of conversations refreshed.
  - `sync` (bool, default `false`): When true, run in-process (local/dev convenience) for both memory refresh and persona generation.
- Behavior:
  1) If `generate_conversation_memories_if_not_found` is true, call selection helper `get_conversations_needing_memory_for_user(...)`.
  2) If any conversations are selected, execute memory generation using the existing enqueue path (sync or background).
  3) After memory refresh step (or immediately if disabled), enqueue `USER_PERSONA_GENERATION` for the `user_id` (sync or background).
  4) Return counts and mode used.

Notes:
- This route is a focused, user-scoped workflow akin to `generate-memories-for-user/{user_id}` and complements the global `trigger-user-persona-generation` routes.
- The persona save path is idempotent (upsert in `/api/user-personas`), so this covers both generate and regenerate.

#### 1.b Internal read endpoint for user persona (used by Brain)
- Route: `GET /api/internal/users/{user_id}/persona` → 200 or 404
- Response body:
  - `{ id, user_id, persona_data, created_at, updated_at }`
- Reason: Brain already calls this endpoint to fetch persona during chat processing; implementing it unblocks robust persona injection.

### 2) Brain: user persona prompt injection

#### 2.a Placeholder syntax
- `{{USER_PERSONA}}`: inject all allowed top-level keys from the persona JSON as a concise, readable snippet.
- `{{USER_PERSONA__key1__key2__...}}`: inject only the specified allowed top-level keys.

Validation rules:
- Define an allowlist of persona keys in the Brain. Start with:
  - `persona` (string, current output from the persona generator)
  - Future-proof optional keys we may add later, e.g., `inferred_interests`, `learning_patterns`, `personality_traits` (lists of strings). Invalid keys are omitted.
- Missing values render as `[Not available]`.

Render format (mirrors conversation memory):
```
These are some details about the user. `key_name` is "value", `key_name` is "value" ...
```
- Lists join naturally, e.g., `"Topic A, Topic B"`. Quotes are escaped.

#### 2.b Injection utilities (shared, extend existing module)
- Extend `Brain/src/utils/prompt_injection.py` to add persona-specific helpers:
  - `ALLOWED_PERSONA_KEYS: List[str] = ["persona", "inferred_interests", "learning_patterns", "personality_traits"]`
  - `PERSONA_PLACEHOLDER_REGEX = r"\{\{USER_PERSONA(?:__([A-Za-z0-9_]+(?:__[A-Za-z0-9_]+)*))?\}\}"`
  - `extract_persona_placeholders(template) -> List[Tuple[str, List[str]]]`
  - `render_persona_snippet(persona: Dict[str, Any], requested_keys: Optional[List[str]]) -> str` (reuse the same value-formatting helper as memory)
  - `inject_persona_placeholders(template: str, persona: Optional[Dict[str, Any]]) -> str`

#### 2.c Integration points
- Simplified mode: `process_query_entrypoint.generate_simplified_response(...)`
  - Replace current `{{USER_PERSONA}}` block with persona placeholder injection logic:
    - If `"{{USER_PERSONA"` in template, call `inject_persona_placeholders(template, user_persona)`.
- Full pipeline: `core/final_response_generator.generate_initial_response(...)`
  - Update signature to accept `user_persona: Optional[Dict[str, Any]]`.
  - After `_generate_response_prompt(...)`, if `"{{USER_PERSONA"` exists, call `inject_persona_placeholders(...)`.
- Entry point: `Brain/src/main.py`
  - Already fetches persona via `api_service.get_user_persona(user_id)`. Ensure the persona object is passed into both simplified and full-pipeline calls.

Compatibility:
- Templates without persona placeholders are unaffected.
- Placeholders with keys not in allowlist render without those keys; if nothing valid remains, inject a clear fallback message.

---

## API Details

### Backend

1) `POST /api/tasks/generate-persona-for-user/{user_id}`
- Query params: `generate_conversation_memories_if_not_found=true|false`, `only_needing=true|false`, `include_empty=true|false`, `clamp=-1`, `sync=false|true`.
- 202 body (async): `{ "message": "Queued persona generation for user X (refreshed M conversations first)." }`
- 200 body (sync): `{ "message": "Completed persona generation for user X (refreshed M conversations first)." }`

2) `GET /api/internal/users/{user_id}/persona`
- 200 body: `{ id, user_id, persona_data, created_at, updated_at }`
- 404 if none.

### Brain

1) Persona retrieval (already present):
- `api_service.get_user_persona(user_id)` → returns `persona_data` or `None` on 404.

2) Prompt placeholders:
- `{{USER_PERSONA}}` and `{{USER_PERSONA__key1__key2}}` per design above.

---

## Edge Cases & Error Handling
- If `generate_conversation_memories_if_not_found=true` and there are many stale/missing memories, honor `clamp` to avoid large synchronous work.
- If memory refresh fails, still proceed to persona generation and log the partial failure.
- Persona missing at injection time → token replaced with `User persona not available.`
- Invalid persona keys in placeholder → silently omitted; snippet still renders with valid keys.
- Long values are escaped and rendered concisely; add truncation later if needed.

---

## Testing Plan
- Unit tests (Brain):
  - `extract_persona_placeholders` parses tokens correctly.
  - `render_persona_snippet` validates keys, formats lists/strings, escapes quotes.
  - `inject_persona_placeholders` handles `None`/missing/invalid keys.
- Unit tests (Backend):
  - `generate-persona-for-user` route: when flag is on, precomputes conversations via `get_conversations_needing_memory_for_user`, calls memory enqueue, then persona enqueue.
  - Internal persona read returns 404/200 appropriately.
- E2E tests:
  - Create a user with conversations; trigger `generate-persona-for-user` (sync) with `generate_conversation_memories_if_not_found=true`; verify conversation memories upserted first and persona saved.
  - Use a prompt containing `{{USER_PERSONA__persona}}` and verify the injected snippet is present in stored pipeline step prompt.

---

## Rollout & Backward Compatibility
- Non-breaking: adds new routes; existing global persona triggers unchanged.
- Prompt injection is additive; templates without persona placeholders are unaffected.

---

## Implementation Tasks

### Backend
1. Add route: `POST /api/tasks/generate-persona-for-user/{user_id}` in `backend/src/tasks/router.py`.
   - Query params: `generate_conversation_memories_if_not_found`, `only_needing`, `include_empty`, `clamp`, `sync`.
   - Reuse `get_conversations_needing_memory_for_user(...)` and `enqueue_memory_generation_task(...)`.
   - Then call `QueueService.send_user_persona_generation_task(user_id)` (await for sync, background otherwise).
2. Add internal route: `GET /api/internal/users/{user_id}/persona` in `backend/src/internal/router.py`.
   - Returns `{ id, user_id, persona_data, created_at, updated_at }` or 404.
3. (Optional) Small CRUD helper to fetch persona by `user_id` for internal route.
4. Tests: unit + E2E for new routes and memory-pre-refresh behavior.

### Brain
5. Extend `src/utils/prompt_injection.py` with persona helpers and allowlist.
6. In `process_query_entrypoint.generate_simplified_response`, swap the raw `{{USER_PERSONA}}` replacement for `inject_persona_placeholders`.
7. In `core/final_response_generator.generate_initial_response`, accept `user_persona` and inject persona placeholders before LLM call.
8. Ensure `Brain/src/main.py` passes `user_persona` to both simplified and full-pipeline paths (full path currently passes only `conversation_memory`).
9. Tests: unit tests for persona injection utilities; integration tests to ensure placeholders get replaced.

### Optional Enhancements
10. Allow `{{USER_PERSONA_JSON}}` to inject raw `persona_data` JSON (stringified) when needed.
11. Add configurable max-length truncation for injected persona snippets.

---

## Acceptance Criteria
- Backend:
  - `POST /api/tasks/generate-persona-for-user/{user_id}` queues (or runs sync) persona generation and, when enabled, refreshes missing/outdated conversation memories first.
  - `GET /api/internal/users/{user_id}/persona` returns persona or 404.
- Brain:
  - Templates with `{{USER_PERSONA}}` inject all allowed keys or fallback text if missing.
  - Templates with `{{USER_PERSONA__key1__key2}}` inject only requested, validated keys.
  - Invalid keys are safely handled and logged (optional).


