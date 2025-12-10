## 🎯 Implementation Task Tracker

### Phase 1: Database & Infrastructure Setup ✅
- [x] Create Alembic migration file (`add_onboarding_system.py`)
- [x] Add `conversation_visits` table with unique constraint on `(user_id, visit_number)`
- [x] Add `prompt_purpose` column to `prompts` table with index
- [x] Run migration on local database
- [ ] Test rollback migration
- [x] Add new SQLAlchemy models to `backend/src/models.py` (ConversationVisit)
- [x] Verify database schema changes

**Files:** `backend/alembic/versions/38ce817ba776_add_onboarding_system.py`, `backend/src/models.py`

### Phase 2: Prompt Setup & Configuration ✅
- [x] Create 4 new prompt entries in database with `prompt_purpose` values:
  - [x] `visit_1` - First-time user prompt
  - [x] `visit_2` - Second visit prompt (with `{{PREVIOUS_CONVERSATIONS_MEMORY}}`)
  - [x] `visit_3` - Third visit prompt (with `{{PREVIOUS_CONVERSATIONS_MEMORY}}`)
  - [x] `steady_state` - 4+ visits prompt (with `{{USER_PERSONA}}` and `{{PREVIOUS_CONVERSATIONS_MEMORY}}`)
- [x] Write prompt text for each with AI-first message instructions
- [x] Create production versions for each prompt (via script)
- [ ] Test prompt retrieval by purpose
- [ ] Run backfill script for existing conversations (assign visit numbers)

### Phase 3: Backend - Core Helper Functions ✅
- [x] Implement `count_user_conversations(db, user_id)`
- [x] Implement `select_prompt_purpose_for_visit(visit_number)`
- [x] Implement `get_production_prompt_by_purpose(db, prompt_purpose)`
- [x] Implement `has_messages(db, conversation_id)`
- [x] Implement `record_conversation_visit(db, conversation_id, user_id, visit_number)`
- [x] Add IntegrityError handling for race conditions
- [ ] Test all helper functions

**Files:** `backend/src/models.py` (added helper functions)

### Phase 4: Backend - Memory System Enhancement ✅
- [x] Create `GET /api/internal/users/{user_id}/previous-memories` endpoint
- [x] Create `GET /api/internal/conversations/{conversation_id}/prompt` endpoint
- [x] Implement `get_previous_memories_for_user()` CRUD function
- [x] Add environment variables: `MEMORY_GENERATION_TIMEOUT`, `PERSONA_GENERATION_TIMEOUT`, `OPENING_MESSAGE_TIMEOUT`
- [x] Implement `generate_memory_sync(conversation_id, db)` with polling
- [x] Implement `generate_memory_sync_with_retry()` with exponential backoff
- [ ] Test sync memory generation (local)

**Files:** `backend/src/internal/router.py`, `backend/src/config/settings.py`, `backend/src/onboarding/service.py` (new)

### Phase 5: Backend - Persona System Enhancement ✅
- [x] Create `GET /api/internal/users/{user_id}/conversations` endpoint
- [x] Implement `generate_persona_sync(user_id, db)` with polling
- [x] Implement `generate_persona_sync_with_retry()` with exponential backoff
- [ ] Add 3-conversation minimum check before persona generation (will be in Brain)
- [ ] Test sync persona generation (local)

**Files:** `backend/src/internal/router.py`, `backend/src/onboarding/service.py`

### Phase 6: Backend - Conversation Creation Flow ✅
- [x] Update `POST /api/conversations` endpoint with new flow
- [x] Add visit number calculation logic
- [x] Add prompt selection by purpose (not name)
- [x] Add race condition protection with retry logic
- [x] Implement visit 2-3: Loop through ALL previous conversations for memory generation
- [x] Implement visit 4+: Ensure 3+ conversations with messages before persona generation
- [x] Add conversation cleanup on preparation failure (delete conversation)
- [x] Update response schema: `ConversationCreateResponse` with visit_number, preparation_status
- [x] Add comprehensive logging for monitoring
- [ ] Test visit 1 creation (no preparation needed)
- [ ] Test visit 2 creation (memory generation for conversation 1)
- [ ] Test visit 3 creation (memory generation for conversations 1 & 2)
- [ ] Test visit 4 creation (memory + persona generation)
- [ ] Test error scenarios (timeouts, failures → HTTP 503)

**Files:** `backend/src/conversations/router.py`

### Phase 7: Backend - AI Opening Message System ✅
- [x] Create `POST /api/internal/opening_message` callback endpoint
- [x] Update `OpeningMessageCallbackPayload` schema
- [x] Implement `generate_ai_first_message()` helper with direct HTTP (even in production)
- [x] Add polling logic for opening message (120s timeout)
- [ ] Test opening message generation for all visit types
- [ ] Test opening message timeout handling

**Files:** `backend/src/internal/router.py`, `backend/src/onboarding/service.py`, `backend/src/onboarding/schemas.py` (new)

### Phase 8: Backend - Title Auto-Generation ✅
- [x] Implement `generate_title_from_message()` helper
- [x] Update `POST /api/conversations/{conversation_id}/messages` to auto-generate title from first user message
- [x] Add check: only update if title is "New Chat"
- [ ] Test title generation from various message types

**Files:** `backend/src/messages/service.py`

### Phase 9: Backend - Prompt CRUD Updates ✅
- [x] Update `PromptBase`, `PromptCreate`, `PromptUpdate` schemas with `prompt_purpose`
- [x] Update `POST /api/prompts` to accept `prompt_purpose`
- [x] Update `PUT /api/prompts/{id}` to accept `prompt_purpose`
- [x] Create `GET /api/prompts/by-purpose/{purpose}` endpoint
- [ ] Test prompt CRUD with purpose field

### Phase 10: Backend - Visit Number in Responses ✅
- [x] Update `GET /api/conversations/{id}` to include `visit_number`
- [x] Update `GET /api/conversations` to include `visit_number` for each conversation
- [x] Implement `get_conversation_with_visit()` helper
- [x] Implement `get_user_conversations_with_visits()` helper
- [x] Update conversation schemas to include `visit_number`
- [ ] Test conversation endpoints return visit_number

**Files:** `backend/src/conversations/schemas.py`, `backend/src/models.py`, `backend/src/conversations/router.py`

### Phase 11: Backend - Health Check & Monitoring ✅
- [x] Create `GET /health/onboarding` endpoint
- [x] Check all 4 onboarding prompts are configured
- [x] Check Brain connectivity
- [x] Check database connectivity
- [ ] Add structured logging throughout conversation creation flow (already present)
- [ ] Test health check endpoint

### Phase 12: Brain - Memory Placeholder Enhancement ✅
- [x] Add `inject_previous_memories_placeholder()` to `utils/prompt_injection.py`
- [x] Add `PREVIOUS_MEMORY_PLACEHOLDER_REGEX` pattern
- [x] Format previous memories as numbered list
- [ ] Test placeholder injection with 0, 1, 2, 3+ memories
- [ ] Update existing prompt processing to use new placeholder

### Phase 13: Brain - API Service Updates ✅
- [x] Add `get_conversation_prompt(conversation_id)` method to APIService
- [x] Add `get_previous_memories(user_id, exclude_conversation_id)` method to APIService
- [x] Add `get_user_conversations(user_id)` method to APIService
- [x] Add `get_conversation_messages(conversation_id)` method to APIService
- [ ] Test all new APIService methods against backend

### Phase 14: Brain - Opening Message Generation ✅
- [x] Create `POST /generate-opening-message` endpoint
- [x] Add `OpeningMessageRequest` schema
- [x] Implement idempotency check (return existing message if present)
- [x] Fetch conversation's assigned prompt via new internal endpoint
- [x] Fetch previous memories if visit > 1
- [x] Fetch persona if visit >= 4
- [x] Inject placeholders into prompt
- [x] Generate opening message with LLM
- [x] Send callback to backend with message and pipeline data
- [x] Add health check endpoint to Brain
- [ ] Test opening message for all visit types (1, 2, 3, 4+)
- [ ] Test idempotency (duplicate requests)

### Phase 15: Brain - Persona Generation Constraint ✅
- [x] Update `generate_user_persona()` in `core/user_persona_generator.py`
- [x] Add conversation count check (minimum 3)
- [x] Skip persona generation if < 3 conversations
- [ ] Test persona generation with 2, 3, 4 conversations

### Phase 16: Brain - Memory Generation Updates ✅
- [x] Update memory generation to skip empty conversations
- [x] Add `has_messages` check before processing
- [x] Add appropriate logging for skipped conversations
- [ ] Test memory generation with empty conversations

### Phase 17: Frontend - Conversation Schema Updates ✅
- [x] Update conversation TypeScript types to include `visit_number`
- [x] Update conversation TypeScript types to include `ai_opening_message`
- [x] Update conversation TypeScript types to include `preparation_status`
- [x] Update conversation TypeScript types to include `requires_opening_message`
- [x] Update conversation TypeScript types to include `prompt_version_id` 
- [x] Update API service calls to handle new response fields (via ConversationCreateResponse type)

### Phase 18: Frontend - Conditional Sidebar ✅
- [x] Add `currentVisitNumber` state to ChatContext
- [x] Update sidebar rendering logic to check `currentVisitNumber >= 4`
- [x] Hide sidebar for visit 1, 2, 3
- [x] Show sidebar for visit 4+
- [x] Hide toggle button for visits 1-3
- [x] Fix layout when sidebar is hidden (proper padding and spacing)
- [x] Fix MessageInput positioning based on sidebar visibility
- [ ] Test sidebar visibility for different visit numbers

### Phase 19: Frontend - AI-First Message Display ✅
- [x] Update ChatContext to handle ConversationCreateResponse with AI opening message
- [x] Add `preparationStatus` and `isPreparingConversation` state to ChatContext
- [x] Add `isInitializingForNewUser` state for smooth loading experience
- [x] Set visit number when conversation is created or selected
- [x] Display AI opening message immediately when conversation is created
- [x] Disable message input until opening message loads (or during preparation)
- [x] Add loading state based on `preparation_status`:
  - [x] Show "Reviewing your previous conversations..." for `generating_memory`
  - [x] Show "Understanding your learning style..." for `generating_persona`
  - [x] Show "Your coach is preparing to meet you..." for `ready`
- [x] Update MessageList to show preparation status messages
- [x] Update MessageInput to accept isDisabled prop
- [x] Auto-create first conversation on login for new users
- [x] Show smooth loading screen during initialization
- [ ] Test AI-first message display for all visit types

### Phase 20: Frontend - Error Handling ✅
- [x] Add error handling for conversation creation failures (HTTP 503)
- [x] Display user-friendly error message: "Unable to prepare your conversation at this time. Please try again in a moment."
- [x] Preserve status code in API error for 503 detection
- [ ] Add retry button for failed conversation creation
- [ ] Test error scenarios (timeout, preparation failure)

### Phase 21: Frontend - Prompt Manager Updates ✅
- [x] Add `prompt_purpose` field to PromptFormData interface
- [x] Add dropdown/select for prompt purpose in prompt creation form
- [x] Add dropdown/select for prompt purpose in prompt editing form
- [x] Options: `visit_1`, `visit_2`, `visit_3`, `steady_state`, `general`, `null`
- [x] Add visual indicators (chips/badges) for visit-based prompts in list view
- [x] Update API calls to include `prompt_purpose` field
- [x] Updated PromptVersionsView to show all prompts with grid layout
- [x] Added create/edit prompt dialogs with purpose selection
- [x] Added color-coded chips for different visit purposes
- [ ] Test creating prompts with different purposes
- [ ] Test updating prompt purposes

### Phase 22: Infrastructure - Timeout Configuration ✅
- [x] Update Lambda timeout to 180 seconds (3 minutes) in `terraform/backend.tf`
- [x] Update Lambda timeout to 180 seconds in `terraform/brain.tf`
- [x] **Note:** API Gateway HTTP API has a fixed 30-second timeout (AWS limitation). This cannot be changed. The architecture uses async processing (SQS) and polling for operations that take longer than 30 seconds.
- [ ] Verify timeout settings in production environment
- [ ] Test that long-running operations don't timeout prematurely

**Files Modified:** 
- `terraform/backend.tf` - Backend Lambda timeout: 300s → 180s
- `terraform/brain.tf` - Brain Lambda timeout: 300s → 180s (via local.lambda_timeout_seconds)

### Phase 23: Testing - Backend Unit Tests
- [ ] Test visit number calculation for new users
- [ ] Test visit number calculation for existing users
- [ ] Test race condition handling (concurrent conversation creation)
- [ ] Test sync memory generation with retry
- [ ] Test sync persona generation with retry
- [ ] Test empty conversation skipping
- [ ] Test timeout handling (memory, persona, opening message)
- [ ] Test prompt selection by purpose (not name)
- [ ] Test conversation cleanup on failure

### Phase 24: Testing - Brain Unit Tests
- [ ] Test `{{PREVIOUS_CONVERSATIONS_MEMORY}}` placeholder injection
- [ ] Test previous memories formatting
- [ ] Test opening message generation
- [ ] Test opening message idempotency
- [ ] Test persona generation with < 3 conversations
- [ ] Test memory generation skips empty conversations

### Phase 25: Testing - E2E Tests
- [ ] E2E: Visit 1 flow (AI greets first, no sidebar, no memory/persona)
- [ ] E2E: Visit 2 flow (memory generated for conv 1, injected into prompt)
- [ ] E2E: Visit 3 flow (memories from conv 1 & 2 injected)
- [ ] E2E: Visit 4 flow (persona generated, sidebar visible)
- [ ] E2E: Visit 5+ flow (steady state behavior)
- [ ] E2E: Empty conversation handling (visit 2 with empty conv 1)
- [ ] E2E: Concurrent conversation creation (race condition)
- [ ] E2E: Timeout scenarios (503 errors)
- [ ] E2E: Title auto-generation from first message

### Phase 26: Deployment & Monitoring
- [ ] Deploy backend changes to staging
- [ ] Deploy Brain changes to staging
- [ ] Deploy frontend changes to staging
- [ ] Run E2E tests against staging
- [ ] Monitor CloudWatch logs for errors
- [ ] Check health endpoint: `GET /health/onboarding`
- [ ] Verify metrics/logging working correctly
- [ ] Deploy to production (backend, brain, frontend)
- [ ] Monitor production for first 24 hours
- [ ] Check success metrics (visit completion rates, memory generation success, etc.)

### Phase 27: Documentation & Cleanup
- [x] Update onboarding_journey.md with implementation details
- [x] Update task_list.md to reflect completion status
- [ ] Update project-context.md with onboarding system overview
- [ ] Document new environment variables in README
- [ ] Create runbook for troubleshooting onboarding issues
- [ ] Document prompt purpose values and usage
- [ ] Add examples of onboarding prompts (templates)
- [ ] Update API documentation with new endpoints
- [ ] Create metrics dashboard for onboarding journey

### Phase 28: Bug Fixes & UX Improvements ✅
**Completed in October 2025 Implementation Session**

- [x] Fix Brain import error (OpeningMessageRequest missing)
- [x] Set production versions for all 4 onboarding prompts
- [x] Implement auto-conversation creation on login
- [x] Add smooth loading screen for new users (`isInitializingForNewUser`)
- [x] Fix chat layout when sidebar is hidden:
  - [x] ChatMessage.tsx padding issues
  - [x] MessageInput.tsx conditional sidebar offset
  - [x] ChatInterface.tsx dynamic width handling
- [x] Create debug info panel component
- [x] Track `currentPromptVersionId` in ChatContext
- [x] Display debug info when `?debug=true` in URL:
  - [x] Visit number
  - [x] Prompt purpose
  - [x] Prompt version ID
- [x] Fix query parameter preservation:
  - [x] Login.tsx - preserve params on login redirect
  - [x] App.tsx - preserve params on auth redirect
- [x] Add `prompt_version_id` to Conversation TypeScript interface

**Files Created:**
- `curiosity-coach-frontend/src/components/DebugInfo.tsx`

**Files Modified:**
- `Brain/src/main.py`
- `curiosity-coach-frontend/src/context/ChatContext.tsx`
- `curiosity-coach-frontend/src/components/ChatInterface/ChatInterface.tsx`
- `curiosity-coach-frontend/src/components/ChatInterface/MessageInput.tsx`
- `curiosity-coach-frontend/src/components/ChatMessage.tsx`
- `curiosity-coach-frontend/src/components/Login.tsx`
- `curiosity-coach-frontend/src/App.tsx`
- `curiosity-coach-frontend/src/types/index.ts`