# Onboarding Journey: Visit-Based Prompts & Memory System

## Overview

Implement a progressive onboarding journey that adapts system prompts based on user visit count (1st, 2nd, 3rd, 4+ visits), generates and injects previous conversation memories, auto-generates initial AI messages, and conditionally displays UI elements.



---

## Key Concepts

- **Visit Number**: Count of conversations for a user. Visit N = (conversation count + 1) when creating a new conversation.
- **Visit 1-3**: Onboarding phase with distinct prompts per visit.
- **Visit 4+**: Steady state with persona-based personalization.
- **Previous Memories**: For visit N, inject memories from conversations 1 through N-1.
- **AI-First Message**: AI sends opening message based on system prompt, not user.

## Design Decisions & Critical Fixes

This section documents important design decisions and critical issues addressed in the plan:

### 1. Visit 3 Memory Generation
**Issue:** Original plan only handled visit 2 memory generation, missing visit 3.

**Fix:** Loop through ALL previous conversations (1 through N-1) to ensure every past conversation has a memory before using them in prompts.

### 2. Empty Conversation Check
**Issue:** Attempting to generate memory for conversations with zero messages.

**Fix:** Added `has_messages()` check before calling memory generation. Skip empty conversations with appropriate logging.

### 3. Opening Message Synchronous Requirement
**Issue:** Opening messages must complete before user can interact, but SQS is asynchronous.

**Fix:** Always use direct HTTP to Brain for opening messages, even in production. Opening message generation is a synchronous operation that blocks conversation creation.

### 4. Race Condition on Visit Number
**Issue:** Concurrent conversation creation could result in duplicate visit numbers.

**Fix:** Use `SELECT FOR UPDATE` database lock on user record during visit number calculation and conversation creation.

### 5. Retry Logic for Sync Operations
**Issue:** Network failures or temporary issues could cause memory/persona generation to fail.

**Fix:** Implemented `generate_memory_sync_with_retry()` and `generate_persona_sync_with_retry()` with exponential backoff.

### 6. Progress Indicators
**Addition:** Return `preparation_status` field in conversation creation response to inform frontend of backend processing state.

### 7. Prompt Purpose Identification
**Clarification:** Added `prompt_purpose` column to `prompts` table to support querying prompts by visit type. Prompts are queried by `prompt_purpose` value (not by name), allowing flexible naming while maintaining structure. Values: `visit_1`, `visit_2`, `visit_3`, `steady_state`, `general`.

### 8. Persona Generation Memory Dependencies
**Critical Fix:** Before generating persona at visit 4+, ensure conversation memories exist for at least 3 conversations. Persona generation requires memories as input.

### 9. Race Condition Protection
**Fix:** Use database unique constraint on `(user_id, visit_number)` instead of transaction locks. Simpler approach that prevents duplicate visit numbers with retry logic on conflict.

### 10. Opening Message Idempotency
**Fix:** Brain checks if opening message already exists before generating a new one. Prevents duplicate messages if backend retries due to network issues.

### 11. Error Handling Strategy
**Decision:** If memory/persona generation fails after retries, conversation creation should fail with HTTP 503 error. User sees error message and must retry. No fallback to generic prompts.

### 12. Title Auto-Generation
**Clarification:** Titles are auto-generated from user's first message, not at conversation creation. Conversations start as "New Chat".

### 13. Remove Current Conversation Memory
**Clarification:** Removed `{{CONVERSATION_MEMORY}}` from onboarding prompts as it doesn't make sense to inject memory of ongoing conversation. New `{{PREVIOUS_CONVERSATIONS_MEMORY}}` placeholder only injects past conversations.

### 14. Monitoring & Logging
**Addition:** Added comprehensive logging at key points (visit start, memory generation, persona generation, timeouts) for debugging and metrics.

## Database Changes

### New Table: `conversation_visits`

Track visit number at conversation creation time.

```sql
CREATE TABLE conversation_visits (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER UNIQUE NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    visit_number INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_conversation_visits_conversation_id ON conversation_visits(conversation_id);
CREATE INDEX idx_conversation_visits_visit_number ON conversation_visits(visit_number);
CREATE UNIQUE INDEX idx_conversation_visits_user_visit ON conversation_visits(user_id, visit_number);
```

**Why separate table?** Maintains immutability of visit number even if conversations are deleted.

**Why unique constraint on (user_id, visit_number)?** Prevents race conditions where concurrent requests could assign duplicate visit numbers to the same user.

### Modified Table: `prompts`

Add new column to identify prompt purpose/visit number:

```sql
ALTER TABLE prompts ADD COLUMN prompt_purpose VARCHAR(50);
-- Values: 'visit_1', 'visit_2', 'visit_3', 'steady_state', 'general' (or NULL)
CREATE INDEX idx_prompts_purpose ON prompts(prompt_purpose);
```

**Why this change?** Allows backend to query prompts by purpose/visit type while allowing flexible prompt names. System queries by `prompt_purpose` value, not by prompt name. Supports active/production version testing per visit type.

### Existing Tables - No Schema Changes

- `conversations`: Use existing `prompt_version_id` for visit-based prompts
- `conversation_memories`: Use existing structure
- `user_personas`: Use existing structure with 3+ conversation constraint

## Prompt Management

### New Prompt Types

Create 4 new prompt entries in `prompts` table. The prompt **names** can be anything (e.g., "First Time User Greeting", "Onboarding V2", etc.), but their `prompt_purpose` must be set correctly:

1. **Purpose:** `visit_1` - First-time user greeting/introduction
2. **Purpose:** `visit_2` - Second visit with context from first conversation
3. **Purpose:** `visit_3` - Third visit with context from first two conversations
4. **Purpose:** `steady_state` - 4+ visits with full persona context

Each prompt should have a production version that includes:
- Appropriate placeholders (`{{PREVIOUS_CONVERSATIONS_MEMORY}}`, `{{USER_PERSONA}}`)
- AI-first message instructions
- Visit-specific guidance tone

**Note:** These prompts support both active (testing) and production versions for A/B testing different onboarding flows. Use the existing prompt versioning system.

### Prompt Selection Logic

In conversation creation flow:
1. Count user's existing conversations → N
2. Visit number = N + 1
3. Select prompt by purpose:
   - Visit 1: Query for `prompt_purpose = 'visit_1'`
   - Visit 2: Query for `prompt_purpose = 'visit_2'`
   - Visit 3: Query for `prompt_purpose = 'visit_3'`
   - Visit 4+: Query for `prompt_purpose = 'steady_state'`
4. Get production version of that prompt
5. Store `prompt_version_id` in conversation record

## Memory System Enhancement

### Current State Clarification

**Existing behavior:** `{{CONVERSATION_MEMORY}}` injects memory of THE CURRENT conversation.

**Change:** We're removing `{{CONVERSATION_MEMORY}}` from the onboarding prompts as it doesn't make sense to inject current conversation memory while the conversation is still ongoing.

**New requirement:** Inject memories from ALL PREVIOUS conversations (not current) via new placeholder.

**Note:** The `{{CONVERSATION_MEMORY}}` functionality is still used internally by persona generation to fetch all conversation memories.

### New Placeholder: `{{PREVIOUS_CONVERSATIONS_MEMORY}}`

**Purpose:** Inject concatenated memories from user's previous conversations (1 through N-1 for visit N).

**Implementation Strategy:**

#### Backend Changes

**New endpoint 1:** `GET /api/internal/users/{user_id}/previous-memories?exclude_conversation_id={conversation_id}`

Returns list of `ConversationMemoryData` objects from all user's conversations except the current one, ordered chronologically.

**New endpoint 2:** `GET /api/internal/conversations/{conversation_id}/prompt`

Returns the prompt text for a conversation's assigned prompt_version_id. Brain uses this to fetch the visit-based prompt for opening message generation.

```python
@router.get("/api/internal/conversations/{conversation_id}/prompt")
async def get_conversation_prompt(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint: Return prompt text for a conversation's assigned prompt version.
    Used by Brain for opening message generation.
    """
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if not conversation.prompt_version_id:
        # Fallback to simplified_conversation if no prompt assigned
        prompt = db.query(Prompt).filter(Prompt.name == "simplified_conversation").first()
        if not prompt:
            raise HTTPException(status_code=500, detail="No valid prompt found")
        prompt_version = db.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt.id,
            PromptVersion.is_production == True
        ).first()
    else:
        prompt_version = db.query(PromptVersion).get(conversation.prompt_version_id)
    
    if not prompt_version:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    
    return {
        "prompt_text": prompt_version.prompt_text,
        "version_number": prompt_version.version_number,
        "prompt_id": prompt_version.prompt_id
    }
```

```python
def get_previous_memories_for_user(
    db: Session, 
    user_id: int, 
    exclude_conversation_id: Optional[int] = None
) -> List[ConversationMemory]:
    """
    Fetch all conversation memories for a user's conversations.
    Optionally exclude a specific conversation (current one).
    Order by conversation creation date ascending.
    """
    query = (
        db.query(ConversationMemory)
        .join(Conversation)
        .filter(Conversation.user_id == user_id)
    )
    if exclude_conversation_id:
        query = query.filter(Conversation.id != exclude_conversation_id)
    
    return query.order_by(Conversation.created_at.asc()).all()

@router.get("/api/internal/users/{user_id}/previous-memories")
async def get_user_previous_memories(
    user_id: int,
    exclude_conversation_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint: Return all conversation memories for a user.
    Optionally exclude a specific conversation (typically the current one).
    Used by Brain for {{PREVIOUS_CONVERSATIONS_MEMORY}} placeholder injection.
    """
    memories = get_previous_memories_for_user(
        db=db,
        user_id=user_id,
        exclude_conversation_id=exclude_conversation_id
    )
    
    return {
        "user_id": user_id,
        "count": len(memories),
        "memories": [
            {
                "conversation_id": mem.conversation_id,
                "memory_data": mem.memory_data,
                "created_at": mem.created_at.isoformat()
            }
            for mem in memories
        ]
    }
```

#### Brain Service Updates

**Add new methods to `Brain/src/services/api_service.py`:**

```python
class APIService:
    # ... existing methods ...
    
    def get_conversation_prompt(self, conversation_id: int) -> Dict[str, Any]:
        """
        Fetch the prompt text for a conversation's assigned prompt version.
        Used for opening message generation.
        """
        url = f"{self.backend_base_url}/api/internal/conversations/{conversation_id}/prompt"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching conversation prompt: {e}")
            raise
    
    def get_previous_memories(
        self, 
        user_id: int, 
        exclude_conversation_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all previous conversation memories for a user.
        Excludes the specified conversation (current one).
        Returns list of memory data objects ordered chronologically.
        """
        url = f"{self.backend_base_url}/api/internal/users/{user_id}/previous-memories"
        params = {}
        if exclude_conversation_id:
            params["exclude_conversation_id"] = exclude_conversation_id
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [mem["memory_data"] for mem in data.get("memories", [])]
        except requests.RequestException as e:
            logger.warning(f"Error fetching previous memories: {e}")
            return []  # Return empty list on error (graceful degradation)
```

#### Brain Changes

**New utility in `src/utils/prompt_injection.py`:**

```python
PREVIOUS_MEMORY_PLACEHOLDER_REGEX = re.compile(
    r"\{\{PREVIOUS_CONVERSATIONS_MEMORY\}\}"
)

def inject_previous_memories_placeholder(
    template: str, 
    memories: Optional[List[Dict[str, Any]]]
) -> str:
    """
    Replace {{PREVIOUS_CONVERSATIONS_MEMORY}} with formatted list of previous memories.
    Format: Numbered list of conversations with their memory data.
    """
    if not PREVIOUS_MEMORY_PLACEHOLDER_REGEX.search(template):
        return template
    
    if not memories or len(memories) == 0:
        fallback = "No previous conversation history available."
        return template.replace(
            "{{PREVIOUS_CONVERSATIONS_MEMORY}}", 
            fallback
        )
    
    # Format as numbered list
    formatted = "Previous conversations:\n"
    for idx, memory in enumerate(memories, 1):
        topics = ", ".join(memory.get("main_topics", []))
        action = ", ".join(memory.get("action", []))
        observation = memory.get("typical_observation", "")
        
        formatted += f"{idx}. Topics: {topics}"
        if action:
            formatted += f" | Actions: {action}"
        if observation:
            formatted += f" | Observation: {observation}"
        formatted += "\n"
    
    return template.replace(
        "{{PREVIOUS_CONVERSATIONS_MEMORY}}", 
        formatted.strip()
    )
```

**Integration in `process_query_entrypoint.py`:**
- Fetch previous memories from backend before processing
- Inject into prompt template after loading production version
- Pass to LLM

## Conversation Creation Flow (Backend)

### Current Flow
```
POST /api/conversations
→ create_conversation(user_id, title)
→ return conversation
```

### Enhanced Flow with Sync Memory Generation

```python
@router.post("", response_model=schemas.ConversationCreateResponse)
async def create_new_conversation(
    conversation_data: Optional[schemas.ConversationCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create conversation with visit tracking and memory pre-generation.
    Uses unique constraint to prevent race conditions.
    """
    preparation_status = "ready"
    
    # 1. Calculate visit number (inside transaction for atomicity)
    conversation_count = count_user_conversations(db, current_user.id)
    visit_number = conversation_count + 1
    
    logger.info(f"Visit {visit_number} started", extra={
        "user_id": current_user.id,
        "visit_number": visit_number,
        "memory_generation_required": visit_number >= 2,
        "persona_generation_required": visit_number >= 4
    })
    
    # 2. Select appropriate prompt by purpose
    prompt_purpose = select_prompt_purpose_for_visit(visit_number)
    prompt_version = get_production_prompt_by_purpose(db, prompt_purpose)
    
    # 3. Create conversation and visit record in same transaction
    conversation = create_conversation(
        db=db,
        user_id=current_user.id,
        title="New Chat",  # Will be auto-generated from user's first message
        prompt_version_id=prompt_version.id if prompt_version else None
    )
    
    # 4. Record visit number with race condition protection via unique constraint
    try:
        record_conversation_visit(db, conversation.id, current_user.id, visit_number)
        db.commit()
    except IntegrityError:
        # Race condition detected: another request assigned same visit number
        db.rollback()
        logger.warning(f"Race condition detected for user {current_user.id}, retrying with updated visit number")
        # Recalculate and retry
        visit_number = count_user_conversations(db, current_user.id) + 1
        record_conversation_visit(db, conversation.id, current_user.id, visit_number)
        db.commit()
    
    # 5. Handle visit-specific requirements (OUTSIDE transaction, fail hard on errors)
    try:
        if visit_number >= 2 and visit_number <= 3:
            preparation_status = "generating_memory"
            # Ensure ALL previous conversations have memories
            previous_conversations = get_user_conversations(db, current_user.id)[:-1]  # Exclude current
            
            for prev_conv in previous_conversations:
                # Check if conversation has messages before generating memory
                if has_messages(db, prev_conv.id):
                    memory = get_memory_for_conversation(db, prev_conv.id)
                    if not memory:
                        # Sync memory generation with retry - BLOCKING
                        generate_memory_sync_with_retry(
                            conversation_id=prev_conv.id,
                            db=db,
                            max_retries=2
                        )
                else:
                    logger.info(f"Skipping memory generation for empty conversation {prev_conv.id}")
        
        elif visit_number >= 4:
            # At visit 4+, user has completed 3+ conversations
            preparation_status = "generating_persona"
            
            # FIRST: Ensure memories exist for at least 3 conversations with messages
            conversations_with_messages = [
                c for c in get_user_conversations(db, current_user.id)[:-1]  # Exclude current
                if has_messages(db, c.id)
            ][:3]  # Take first 3 conversations with messages
            
            if len(conversations_with_messages) < 3:
                logger.error(f"User {current_user.id} has fewer than 3 conversations with messages")
                raise HTTPException(
                    status_code=503,
                    detail="Unable to prepare your personalized experience. Please ensure you have completed at least 3 conversations."
                )
            
            # Generate missing memories for these conversations
            for conv in conversations_with_messages:
                memory = get_memory_for_conversation(db, conv.id)
                if not memory:
                    generate_memory_sync_with_retry(
                        conversation_id=conv.id,
                        db=db,
                        max_retries=2
                    )
            
            # THEN: Generate persona if not exists
            persona = get_user_persona(db, current_user.id)
            if not persona:
                # Sync persona generation with retry - BLOCKING
                generate_persona_sync_with_retry(
                    user_id=current_user.id,
                    db=db,
                    max_retries=2
                )
        
        # 6. Generate AI's opening message
        preparation_status = "ready"
        ai_opening_message = await generate_ai_first_message(
            conversation_id=conversation.id,
            user_id=current_user.id,
            visit_number=visit_number,
            db=db
        )
        
    except (TimeoutError, HTTPException) as e:
        # Clean up: delete the conversation if preparation fails
        db.delete(conversation)
        db.commit()
        
        if isinstance(e, HTTPException):
            raise e
        
        logger.error(f"Conversation preparation failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to prepare your conversation at this time. Please try again in a moment."
        )
    
    # 7. Return conversation with visit info, opening message, and status
    return {
        "conversation": conversation,
        "visit_number": visit_number,
        "ai_opening_message": ai_opening_message,
        "preparation_status": preparation_status,
        "requires_opening_message": True
    }
```

### Helper Functions

**`count_user_conversations(db, user_id) -> int`**
```python
def count_user_conversations(db: Session, user_id: int) -> int:
    return db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).count()
```

**`select_prompt_purpose_for_visit(visit_number: int) -> str`**
```python
def select_prompt_purpose_for_visit(visit_number: int) -> str:
    """Returns the prompt PURPOSE to query by"""
    if visit_number == 1:
        return "visit_1"
    elif visit_number == 2:
        return "visit_2"
    elif visit_number == 3:
        return "visit_3"
    else:
        return "steady_state"
```

**`get_production_prompt_by_purpose(db, prompt_purpose) -> PromptVersion`**
```python
def get_production_prompt_by_purpose(db: Session, prompt_purpose: str):
    """Get production prompt version by purpose"""
    prompt = db.query(Prompt).filter(
        Prompt.prompt_purpose == prompt_purpose
    ).first()
    
    if not prompt:
        logger.warning(f"No prompt found for purpose {prompt_purpose}, falling back to simplified_conversation")
        prompt = db.query(Prompt).filter(Prompt.name == "simplified_conversation").first()
        if not prompt:
            raise HTTPException(status_code=500, detail="No valid prompt found")
    
    # Get production version
    production_version = db.query(PromptVersion).filter(
        PromptVersion.prompt_id == prompt.id,
        PromptVersion.is_production == True
    ).first()
    
    if not production_version:
        # Fallback to latest version if no production version set
        production_version = db.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt.id
        ).order_by(PromptVersion.version_number.desc()).first()
    
    return production_version
```

**`has_messages(db, conversation_id) -> bool`**
```python
def has_messages(db: Session, conversation_id: int) -> bool:
    """
    Check if a conversation has any messages.
    """
    message_count = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).count()
    return message_count > 0
```

**`record_conversation_visit(db, conversation_id, user_id, visit_number)`**
```python
def record_conversation_visit(db: Session, conversation_id: int, user_id: int, visit_number: int):
    """
    Record visit number for a conversation.
    Raises IntegrityError if (user_id, visit_number) already exists (race condition).
    """
    visit_record = ConversationVisit(
        conversation_id=conversation_id,
        user_id=user_id,
        visit_number=visit_number
    )
    db.add(visit_record)
    # Note: Don't commit here - let caller handle transaction
```

**`generate_memory_sync(conversation_id, db)`**
```python
def generate_memory_sync(conversation_id: int, db: Session):
    """
    Synchronously generate memory for a conversation.
    Calls Brain's /tasks endpoint with GENERATE_MEMORY_BATCH task.
    Blocks until memory is generated or timeout (120s).
    Raises TimeoutError on timeout, HTTPException on other errors.
    """
    brain_endpoint = settings.LOCAL_BRAIN_ENDPOINT_URL or settings.BRAIN_ENDPOINT_URL
    timeout = settings.MEMORY_GENERATION_TIMEOUT  # 120s
    
    # 1. Trigger Brain task
    try:
        response = httpx.post(
            f"{brain_endpoint}/tasks",
            json={
                "task_type": "GENERATE_MEMORY_BATCH",
                "conversation_ids": [conversation_id]
            },
            timeout=timeout
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Error calling Brain for memory generation: {e}")
        raise HTTPException(status_code=503, detail=f"Memory generation request failed: {e}")
    
    # 2. Poll for memory with timeout
    start_time = time.time()
    while time.time() - start_time < timeout:
        memory = get_memory_for_conversation(db, conversation_id)
        if memory:
            logger.info(f"Memory generated for conversation {conversation_id}")
            return memory
        time.sleep(1)  # Poll every second
        db.refresh(db)  # Refresh DB session
    
    raise TimeoutError(f"Memory generation timed out after {timeout}s for conversation {conversation_id}")
```

**`generate_memory_sync_with_retry(conversation_id, db, max_retries)`**
```python
def generate_memory_sync_with_retry(
    conversation_id: int, 
    db: Session, 
    max_retries: int = 2
):
    """
    Synchronously generate memory with retry logic.
    Retries up to max_retries times with exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            return generate_memory_sync(conversation_id, db)
        except TimeoutError:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s...
            logger.info(f"Retrying memory generation for conversation {conversation_id}, attempt {attempt + 2}")
```

**`generate_persona_sync(user_id, db)`**
```python
def generate_persona_sync(user_id: int, db: Session):
    """
    Synchronously generate persona for a user.
    Calls Brain's /tasks endpoint with USER_PERSONA_GENERATION task.
    Blocks until persona is generated or timeout (120s).
    """
    brain_endpoint = settings.LOCAL_BRAIN_ENDPOINT_URL or settings.BRAIN_ENDPOINT_URL
    timeout = settings.PERSONA_GENERATION_TIMEOUT  # 120s
    
    # 1. Trigger Brain task
    try:
        response = httpx.post(
            f"{brain_endpoint}/tasks",
            json={
                "task_type": "USER_PERSONA_GENERATION",
                "user_ids": [user_id]
            },
            timeout=timeout
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Error calling Brain for persona generation: {e}")
        raise HTTPException(status_code=503, detail=f"Persona generation request failed: {e}")
    
    # 2. Poll for persona with timeout
    start_time = time.time()
    while time.time() - start_time < timeout:
        persona = get_user_persona(db, user_id)
        if persona:
            logger.info(f"Persona generated for user {user_id}")
            return persona
        time.sleep(1)  # Poll every second
        db.refresh(db)  # Refresh DB session
    
    raise TimeoutError(f"Persona generation timed out after {timeout}s for user {user_id}")
```

**`generate_persona_sync_with_retry(user_id, db, max_retries)`**
```python
def generate_persona_sync_with_retry(
    user_id: int, 
    db: Session, 
    max_retries: int = 2
):
    """
    Synchronously generate persona with retry logic.
    Retries up to max_retries times with exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            return generate_persona_sync(user_id, db)
        except TimeoutError:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
            logger.info(f"Retrying persona generation for user {user_id}, attempt {attempt + 2}")
```

## AI-First Message Flow

### Brain Changes

**New endpoint:** `POST /generate-opening-message`

```python
@app.post("/generate-opening-message")
async def generate_opening_message(payload: OpeningMessageRequest):
    """
    Generate AI's first message for a new conversation.
    Uses the conversation's assigned visit-based prompt (visit_1, visit_2, visit_3, or steady_state).
    Idempotent: Returns existing message if already generated.
    
    Payload: {
        "conversation_id": int,
        "user_id": int,
        "visit_number": int,
        "callback_url": str
    }
    """
    # 0. Check if opening message already exists (idempotency)
    existing_messages = api_service.get_conversation_messages(payload.conversation_id)
    if existing_messages and len(existing_messages) > 0:
        logger.info(f"Opening message already exists for conversation {payload.conversation_id}")
        return {
            "status": "already_exists",
            "message": existing_messages[0]["content"]
        }
    
    # 1. Fetch conversation's assigned prompt (visit-based prompt with opening message instructions)
    prompt_response = api_service.get_conversation_prompt(payload.conversation_id)
    prompt_text = prompt_response["prompt_text"]
    
    # 2. Fetch previous memories if visit > 1
    previous_memories = None
    if payload.visit_number > 1:
        previous_memories = api_service.get_previous_memories(
            payload.user_id, 
            payload.conversation_id
        )
    
    # 3. Fetch persona if visit >= 4
    persona = None
    if payload.visit_number >= 4:
        persona = api_service.get_user_persona(payload.user_id)
    
    # 4. Inject placeholders into prompt
    prompt_text = inject_previous_memories_placeholder(prompt_text, previous_memories)
    prompt_text = inject_persona_placeholders(prompt_text, persona)
    
    # 5. Generate opening message with LLM
    # The visit-based prompt is designed to produce a welcoming opening message
    # that uses persona/memory context if available
    opening_message_response = llm_service.generate_response(
        prompt_text=prompt_text,
        user_message="",  # No user message for opening
        conversation_history=[],  # Empty history for first message
        json_mode=False
    )
    opening_message = opening_message_response["content"]
    
    # 6. Send callback to backend with AI message and pipeline data
    api_service.send_callback(
        callback_url=payload.callback_url,
        payload={
            "conversation_id": payload.conversation_id,
            "ai_message": opening_message,
            "is_opening_message": True,
            "pipeline_data": {
                "prompt_used": prompt_text,
                "visit_number": payload.visit_number,
                "had_previous_memories": previous_memories is not None,
                "had_persona": persona is not None
            }
        }
    )
    
    return {"status": "success", "message": opening_message}
```

### Backend Integration

**`generate_ai_first_message()` helper:**
```python
async def generate_ai_first_message(
    conversation_id: int,
    user_id: int,
    visit_number: int,
    db: Session
) -> str:
    """
    Trigger Brain to generate opening message and wait for it.
    Raises TimeoutError if generation fails.
    
    IMPORTANT: Opening messages MUST be synchronous (user is waiting during 
    conversation creation), so we use direct HTTP to Brain even in production.
    """
    callback_url = f"{settings.BACKEND_CALLBACK_BASE_URL}/api/internal/opening_message"
    
    # ALWAYS use direct HTTP for opening messages (synchronous requirement)
    brain_endpoint = (
        settings.LOCAL_BRAIN_ENDPOINT_URL 
        if settings.APP_ENV == "development" 
        else settings.BRAIN_ENDPOINT_URL  # Production Brain HTTP endpoint
    )
    
    timeout = settings.OPENING_MESSAGE_TIMEOUT  # 120s
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{brain_endpoint}/generate-opening-message",
                json={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "visit_number": visit_number,
                    "callback_url": callback_url
                },
                timeout=timeout
            )
            response.raise_for_status()
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"Error calling Brain for opening message: {e}")
        raise TimeoutError(f"Failed to request opening message generation: {e}")
    
    # Poll for message (with timeout)
    start_time = time.time()
    while time.time() - start_time < timeout:
        await asyncio.sleep(1)
        messages = get_conversation_messages(db, conversation_id)
        if messages and not messages[0].is_user:
            logger.info(f"Opening message generated successfully for conversation {conversation_id}")
            return messages[0].content
    
    # Timeout - raise error
    logger.error(f"Opening message timeout for conversation {conversation_id} after {timeout}s")
    raise TimeoutError(f"Opening message generation timed out after {timeout}s")
```

**New internal endpoint for Brain callback:**
```python
@router.post("/api/internal/opening_message")
async def receive_opening_message(
    payload: OpeningMessageCallbackPayload,
    db: Session = Depends(get_db)
):
    """
    Receive AI opening message from Brain and save to DB.
    Includes pipeline data for debugging and metrics.
    """
    # Create AI message (is_user=False)
    message = create_message(
        db=db,
        conversation_id=payload.conversation_id,
        content=payload.ai_message,
        is_user=False,
        responds_to_message_id=None
    )
    
    # Save pipeline data if provided
    if payload.pipeline_data:
        create_message_pipeline_data(
            db=db,
            message_id=message.id,
            pipeline_data=payload.pipeline_data
        )
    
    logger.info(f"Opening message saved for conversation {payload.conversation_id}", extra={
        "conversation_id": payload.conversation_id,
        "message_id": message.id,
        "is_opening_message": True
    })
    
    return {"status": "success", "message_id": message.id}
```

## Persona Generation Constraint

### Modify Brain's Persona Generation

**File:** `Brain/src/core/user_persona_generator.py`

Add check before generating:
```python
def generate_user_persona(user_id: int, api_service: APIService, llm_service: LLMService):
    # 1. Fetch user's conversations via internal endpoint
    conversations = api_service.get_user_conversations(user_id)
    
    # 2. Check minimum threshold
    if len(conversations) < 3:
        logger.info(f"User {user_id} has only {len(conversations)} conversations. "
                   f"Persona requires minimum 3 conversations. Skipping.")
        return None
    
    # 3. Continue with existing persona generation logic
    memories = api_service.get_user_memories(user_id)
    # ... rest of generation
```

### Backend Changes

**New internal endpoint:** `GET /api/internal/users/{user_id}/conversations`

Returns basic conversation list for counting purposes.

```python
@router.get("/api/internal/users/{user_id}/conversations")
async def get_user_conversations_internal(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint: Return list of conversation IDs for a user.
    Used by Brain to check conversation count.
    """
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(Conversation.created_at.asc()).all()
    
    return {
        "user_id": user_id,
        "conversation_count": len(conversations),
        "conversation_ids": [c.id for c in conversations]
    }
```

## Frontend Changes

### Conditional Sidebar Display

**File:** `curiosity-coach-frontend/src/App.tsx`

Track visit number in state and conditionally render sidebar:

```typescript
// In conversation context or App state
const [visitNumber, setVisitNumber] = useState<number | null>(null);

// Fetch visit number when loading conversation
useEffect(() => {
  if (currentConversation) {
    // Visit number is returned in conversation object or separate call
    setVisitNumber(currentConversation.visit_number);
  }
}, [currentConversation]);

// Conditional rendering
<div className="flex h-screen">
  {visitNumber && visitNumber >= 4 && (
    <ConversationSidebar />
  )}
  <ChatInterface />
</div>
```

### Backend Schema Update

**Add `visit_number` to conversation response:**

```python
class ConversationWithVisit(BaseModel):
    id: int
    user_id: int
    title: str
    visit_number: int
    created_at: datetime
    updated_at: datetime
```

**Modify conversation retrieval endpoints:**
- `GET /api/conversations/{id}` - Include visit_number
- `GET /api/conversations` - Include visit_number for each conversation

```python
def get_conversation_with_visit(db: Session, conversation_id: int):
    conversation = get_conversation(db, conversation_id)
    visit_record = db.query(ConversationVisit).filter(
        ConversationVisit.conversation_id == conversation_id
    ).first()
    
    return {
        **conversation.__dict__,
        "visit_number": visit_record.visit_number if visit_record else None
    }
```

### AI-First Message Display

**File:** `curiosity-coach-frontend/src/components/ChatInterface/ChatInterface.tsx`

When opening a new conversation:

```typescript
useEffect(() => {
  if (conversationId && !messages.length) {
    // Load initial message (AI's opening message)
    fetchMessages(conversationId);
  }
}, [conversationId]);

// Don't show input until opening message is loaded
const showInput = messages.length > 0 || loadingOpeningMessage === false;
```

**UI Changes:**
1. Hide message input until AI's opening message appears
2. Show loading state based on `preparation_status`:
   - `"generating_memory"`: "Reviewing your previous conversations..."
   - `"generating_persona"`: "Understanding your learning style..."
   - `"ready"`: "Your coach is preparing to meet you..."
3. Once opening message loads (check `requires_opening_message` field), enable input for user response
4. Display appropriate error message if opening message timeout occurs

### Prompt Manager Updates

#### Backend Prompt CRUD Updates

Update backend schemas and endpoints to support `prompt_purpose`:

**Schema Updates (`backend/src/prompts/schemas.py`):**
```python
class PromptBase(BaseModel):
    name: str
    description: Optional[str] = None
    prompt_purpose: Optional[str] = None  # New field

class PromptCreate(PromptBase):
    pass

class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt_purpose: Optional[str] = None  # New field

class PromptResponse(PromptBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

**Router Updates (`backend/src/prompts/router.py`):**
```python
@router.post("/api/prompts", response_model=schemas.PromptResponse)
async def create_prompt(
    prompt_data: schemas.PromptCreate,
    db: Session = Depends(get_db)
):
    """Create new prompt with optional prompt_purpose"""
    prompt = Prompt(
        name=prompt_data.name,
        description=prompt_data.description,
        prompt_purpose=prompt_data.prompt_purpose  # Include purpose
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt

@router.put("/api/prompts/{prompt_id}", response_model=schemas.PromptResponse)
async def update_prompt(
    prompt_id: int,
    prompt_data: schemas.PromptUpdate,
    db: Session = Depends(get_db)
):
    """Update prompt including prompt_purpose"""
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    if prompt_data.name is not None:
        prompt.name = prompt_data.name
    if prompt_data.description is not None:
        prompt.description = prompt_data.description
    if prompt_data.prompt_purpose is not None:
        prompt.prompt_purpose = prompt_data.prompt_purpose
    
    db.commit()
    db.refresh(prompt)
    return prompt

@router.get("/api/prompts/by-purpose/{purpose}")
async def get_prompts_by_purpose(
    purpose: str,
    db: Session = Depends(get_db)
):
    """Get all prompts with a specific purpose"""
    prompts = db.query(Prompt).filter(Prompt.prompt_purpose == purpose).all()
    return prompts
```

#### Frontend Prompt Manager Updates

**File:** `curiosity-coach-frontend/src/components/PromptVersionsView.tsx`

Add `prompt_purpose` field to prompt creation/editing:

```typescript
interface PromptFormData {
  name: string;
  description?: string;
  prompt_purpose?: 'visit_1' | 'visit_2' | 'visit_3' | 'steady_state' | 'general' | null;
}

// In form UI
<FormControl fullWidth margin="normal">
  <InputLabel>Prompt Purpose</InputLabel>
  <Select
    value={formData.prompt_purpose || ''}
    onChange={(e) => setFormData({...formData, prompt_purpose: e.target.value || null})}
  >
    <MenuItem value="">None (General)</MenuItem>
    <MenuItem value="visit_1">Visit 1 - First Time User</MenuItem>
    <MenuItem value="visit_2">Visit 2 - Second Visit</MenuItem>
    <MenuItem value="visit_3">Visit 3 - Third Visit</MenuItem>
    <MenuItem value="steady_state">Steady State - 4+ Visits</MenuItem>
    <MenuItem value="general">General Purpose</MenuItem>
  </Select>
  <FormHelperText>
    Select the visit type this prompt should be used for. Leave empty for general prompts.
  </FormHelperText>
</FormControl>

// Update API calls to include prompt_purpose
const handleCreatePrompt = async () => {
  await axios.post('/api/prompts', {
    name: formData.name,
    description: formData.description,
    prompt_purpose: formData.prompt_purpose
  });
};

const handleUpdatePrompt = async () => {
  await axios.put(`/api/prompts/${promptId}`, {
    name: formData.name,
    description: formData.description,
    prompt_purpose: formData.prompt_purpose
  });
};
```

**Add visual indicators for visit-based prompts:**
```typescript
// In prompt list display
<Chip 
  label={
    prompt.prompt_purpose === 'visit_1' ? 'Visit 1' :
    prompt.prompt_purpose === 'visit_2' ? 'Visit 2' :
    prompt.prompt_purpose === 'visit_3' ? 'Visit 3' :
    prompt.prompt_purpose === 'steady_state' ? 'Steady State' :
    'General'
  }
  color={prompt.prompt_purpose ? 'primary' : 'default'}
  size="small"
/>
```

## API Schema Changes

### New Request/Response Models

**Backend (`src/conversations/schemas.py`):**

```python
class ConversationWithVisit(BaseModel):
    id: int
    user_id: int
    title: str
    visit_number: int
    ai_opening_message: Optional[str]
    created_at: datetime
    updated_at: datetime

class ConversationCreateResponse(BaseModel):
    conversation: ConversationWithVisit
    visit_number: int
    ai_opening_message: str
    preparation_status: str  # "ready", "generating_memory", "generating_persona"
    requires_opening_message: bool  # Always True for new conversations
```

**Brain (new schemas.py additions):**

```python
class OpeningMessageRequest(BaseModel):
    conversation_id: int
    user_id: int
    visit_number: int
    callback_url: str

class OpeningMessageCallbackPayload(BaseModel):
    conversation_id: int
    ai_message: str
    is_opening_message: bool
    pipeline_data: Optional[dict] = None  # Includes prompt_used, visit_number, context flags
```

## Title Auto-Generation

### Implementation Strategy

**On conversation creation:**
- Create conversation with title "New Chat"
- After user sends first message, auto-generate title from message content

**Backend changes:**

Add to message creation endpoint:
```python
@router.post("/api/conversations/{conversation_id}/messages")
async def create_message(...):
    # ... existing message creation logic
    
    # Auto-generate title from user's first message
    if is_user and conversation.title == "New Chat":
        message_count = count_messages_in_conversation(db, conversation_id)
        if message_count == 1:  # This is the first user message
            new_title = generate_title_from_message(message.content)
            update_conversation_title(db, conversation_id, new_title)
    
    # ... rest of logic
```

**Helper function:**
```python
def generate_title_from_message(content: str, max_length: int = 50) -> str:
    """
    Generate a concise title from message content.
    Takes first sentence or first N characters.
    """
    # Simple implementation: take first sentence up to max_length
    sentences = content.split('.')
    title = sentences[0].strip()
    if len(title) > max_length:
        title = title[:max_length].rsplit(' ', 1)[0] + "..."
    return title or "New Chat"
```

**Future enhancement:** Use LLM to generate more contextual titles.

## Alembic Migration

### Migration File: `add_onboarding_system.py`

```python
"""Add onboarding system with visits and prompt purposes

Revision ID: xxxxxxxxxxxx
Revises: yyyyyyyyyyyy
Create Date: 2025-10-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = 'xxxxxxxxxxxx'
down_revision = 'yyyyyyyyyyyy'
branch_labels = None
depends_on = None

def upgrade():
    # Create conversation_visits table
    op.create_table(
        'conversation_visits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('visit_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_conversation_visits_conversation_id', 'conversation_visits', ['conversation_id'], unique=False)
    op.create_index('idx_conversation_visits_visit_number', 'conversation_visits', ['visit_number'], unique=False)
    op.create_unique_constraint('uq_user_visit', 'conversation_visits', ['user_id', 'visit_number'])
    
    # Add prompt_purpose column to prompts table
    op.add_column('prompts', sa.Column('prompt_purpose', sa.String(length=50), nullable=True))
    op.create_index('idx_prompts_purpose', 'prompts', ['prompt_purpose'], unique=False)

def downgrade():
    # Remove prompt_purpose from prompts
    op.drop_index('idx_prompts_purpose', table_name='prompts')
    op.drop_column('prompts', 'prompt_purpose')
    
    # Remove conversation_visits table
    op.drop_constraint('uq_user_visit', 'conversation_visits', type_='unique')
    op.drop_index('idx_conversation_visits_visit_number', table_name='conversation_visits')
    op.drop_index('idx_conversation_visits_conversation_id', table_name='conversation_visits')
    op.drop_table('conversation_visits')
```

### Running the Migration

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

## Metrics & Monitoring

### Instrumentation Points

Add comprehensive logging and metrics at key decision points:

```python
# backend/src/conversations/router.py

@router.post("", response_model=schemas.ConversationCreateResponse)
async def create_new_conversation(...):
    start_time = time.time()
    
    # Log visit start
    logger.info(f"Visit {visit_number} started", extra={
        "user_id": current_user.id,
        "visit_number": visit_number,
        "memory_generation_required": visit_number >= 2,
        "persona_generation_required": visit_number >= 4,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # ... memory generation ...
    
    if visit_number >= 2:
        memory_start = time.time()
        # generate memories
        memory_duration = (time.time() - memory_start) * 1000
        logger.info(f"Memory generation completed", extra={
            "conversation_id": conversation.id,
            "user_id": current_user.id,
            "duration_ms": memory_duration,
            "success": True
        })
    
    # ... persona generation ...
    
    if visit_number >= 4:
        persona_start = time.time()
        # generate persona
        persona_duration = (time.time() - persona_start) * 1000
        logger.info(f"Persona generation completed", extra={
            "user_id": current_user.id,
            "duration_ms": persona_duration,
            "success": True
        })
    
    # ... opening message ...
    
    opening_start = time.time()
    ai_opening_message = await generate_ai_first_message(...)
    opening_duration = (time.time() - opening_start) * 1000
    
    # Log successful completion
    total_duration = (time.time() - start_time) * 1000
    logger.info(f"Conversation creation completed", extra={
        "conversation_id": conversation.id,
        "user_id": current_user.id,
        "visit_number": visit_number,
        "total_duration_ms": total_duration,
        "memory_duration_ms": memory_duration if visit_number >= 2 else 0,
        "persona_duration_ms": persona_duration if visit_number >= 4 else 0,
        "opening_message_duration_ms": opening_duration,
        "success": True
    })
    
    return {...}
```

### Health Check Endpoint

Add dedicated health check for onboarding preparation system:

```python
# backend/src/health/router.py

@router.get("/health/onboarding")
async def check_onboarding_health(db: Session = Depends(get_db)):
    """
    Health check for onboarding system.
    Validates that all onboarding prompts are configured and Brain is accessible.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check 1: Visit prompts configured
    required_purposes = ["visit_1", "visit_2", "visit_3", "steady_state"]
    for purpose in required_purposes:
        prompt = db.query(Prompt).filter(Prompt.prompt_purpose == purpose).first()
        if prompt:
            production_version = db.query(PromptVersion).filter(
                PromptVersion.prompt_id == prompt.id,
                PromptVersion.is_production == True
            ).first()
            health_status["checks"][f"prompt_{purpose}"] = {
                "configured": True,
                "has_production_version": production_version is not None
            }
        else:
            health_status["checks"][f"prompt_{purpose}"] = {
                "configured": False,
                "has_production_version": False
            }
            health_status["status"] = "degraded"
    
    # Check 2: Brain connectivity
    try:
        brain_endpoint = settings.LOCAL_BRAIN_ENDPOINT_URL or settings.BRAIN_ENDPOINT_URL
        response = httpx.get(f"{brain_endpoint}/health", timeout=5.0)
        health_status["checks"]["brain_connectivity"] = {
            "reachable": response.status_code == 200,
            "endpoint": brain_endpoint
        }
    except Exception as e:
        health_status["checks"]["brain_connectivity"] = {
            "reachable": False,
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check 3: Database connectivity
    try:
        db.execute("SELECT 1")
        health_status["checks"]["database"] = {"connected": True}
    except Exception as e:
        health_status["checks"]["database"] = {"connected": False, "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Return appropriate status code
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)
```

## Migration Plan

### Phase 1: Database & Prompt Setup
1. Create `conversation_visits` table migration (see Alembic migration above)
2. Add `prompt_purpose` column to `prompts` table (included in migration)
3. Create 4 new prompt entries with appropriate `prompt_purpose` values
4. Create production versions for each prompt with appropriate placeholders
5. Backfill `conversation_visits` for existing conversations using this script:

```python
def backfill_conversation_visits(db: Session):
    """
    Backfill conversation_visits for existing conversations.
    Estimate visit number from chronological order per user.
    """
    users = db.query(User).all()
    
    for user in users:
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user.id
        ).order_by(Conversation.created_at.asc()).all()
        
        for idx, conv in enumerate(conversations, start=1):
            existing = db.query(ConversationVisit).filter(
                ConversationVisit.conversation_id == conv.id
            ).first()
            
            if not existing:
                visit_record = ConversationVisit(
                    conversation_id=conv.id,
                    visit_number=idx
                )
                db.add(visit_record)
        
        db.commit()
        logger.info(f"Backfilled {len(conversations)} conversation visits for user {user.id}")
```

### Phase 2: Memory System Enhancement
1. Implement `{{PREVIOUS_CONVERSATIONS_MEMORY}}` placeholder in Brain
2. Add `GET /api/internal/users/{user_id}/previous-memories` endpoint
3. Add injection logic in `prompt_injection.py`
4. Update Brain's query processing to fetch and inject previous memories

### Phase 3: Persona Generation Constraint
1. Add `GET /api/internal/users/{user_id}/conversations` endpoint
2. Modify Brain's persona generator to check conversation count >= 3
3. Add sync persona generation helper in backend

### Phase 4: Conversation Creation Flow
1. Modify `POST /api/conversations` to calculate visit number with transaction locks
2. Implement sync memory generation for visits 2 and 3 (all previous conversations)
3. Implement sync persona generation for visit 4+
4. Add visit number recording logic
5. Update response schemas to include visit info and preparation_status
6. Implement title auto-generation from user's first message in message creation endpoint

### Phase 5: AI-First Message
1. Implement `POST /generate-opening-message` in Brain
2. Add `POST /api/internal/opening_message` callback endpoint in Backend
3. Integrate opening message generation in conversation creation flow
4. Add polling/timeout logic

### Phase 6: Frontend Updates
1. Update `GET /api/conversations/{id}` and `GET /api/conversations` to include visit_number in response
2. Update frontend conversation schemas to include visit_number
3. Implement conditional sidebar display (visit >= 4)
4. Update chat interface to display AI-first message
5. Add loading states for opening message based on preparation_status
6. Hide input until opening message loads
7. Add error handling for conversation creation failures (HTTP 503)
8. Update Prompt Manager UI with `prompt_purpose` dropdown field

### Phase 7: Testing
1. E2E test for visit 1 (no sidebar, AI first message)
2. E2E test for visit 2 (sync memory generation, previous memory injection)
3. E2E test for visit 3 (two previous memories injected)
4. E2E test for visit 4 (persona generation, sidebar visible)
5. Test timeout handling for sync operations
6. Test backfilled conversations work correctly

## Edge Cases & Error Handling

### Timeout Handling (with Retry and Fail-Hard Strategy)
- **Sync memory generation timeout (120s):** Retry up to 2 times with exponential backoff (1s, 2s delays). After final timeout, **delete the conversation** and return HTTP 503 error to user with message: "Unable to prepare your conversation at this time. Please try again in a moment."
- **Sync persona generation timeout (120s):** Retry up to 2 times with exponential backoff. After final timeout, **delete the conversation** and return HTTP 503 error to user.
- **Opening message generation timeout (120s):** **Delete the conversation** and return HTTP 503 error. No fallback messages used.
- **Important:** Ensure API Gateway timeout (150s) and Lambda timeout (180s) are configured higher than these values to prevent premature connection drops.

### Missing Data Scenarios
- **Visit 2 but first conversation has no messages:** Skip memory generation for that conversation with logged info. Use empty memory placeholder in prompt. Opening message still generated (may have minimal context).
- **Visit 3 but only first conversation has messages:** Generate memory only for conversations with messages. Other conversations skipped. Opening message proceeds with available memories.
- **Visit 4+ but fewer than 3 conversations with messages:** **Delete the conversation** and return HTTP 503 error: "Unable to prepare your personalized experience. Please ensure you have completed at least 3 conversations."
- **Prompt version not found:** Use fallback to `simplified_conversation` prompt's production version. If that also doesn't exist, return HTTP 500 error.
- **Memory generation fails validation:** Retry generation. After retries fail, **delete conversation** and return HTTP 503 error.

### Deleted Conversations
- Visit number in `conversation_visits` remains immutable even after conversation deletion
- Visit numbers don't get recalculated when user deletes conversations
- Frontend handles gaps gracefully (e.g., visits 1, 2, 4, 7 if user deleted 3, 5, 6)
- Previous memories endpoint automatically excludes deleted conversations

### Concurrent Requests (Fixed with Unique Constraint)
- **Race condition:** User creates 2 conversations simultaneously, both might try to assign same visit number
- **Solution:** Unique constraint on `(user_id, visit_number)` in database with retry logic
  ```python
  try:
      record_conversation_visit(db, conversation.id, user_id, visit_number)
      db.commit()
  except IntegrityError:
      # Race condition detected: another request assigned same visit number
      db.rollback()
      # Recalculate with updated count and retry
      visit_number = count_user_conversations(db, user_id) + 1
      record_conversation_visit(db, conversation.id, user_id, visit_number)
      db.commit()
  ```
- Database constraint ensures atomic uniqueness
- Retry logic handles the rare case when concurrent requests occur
- Simpler than transaction locks, no blocking

### Empty Conversation Protection
- **Check before memory generation:** Use `has_messages()` to verify conversation has content
- **Skip empty conversations:** Log info message and continue to next conversation
- **Frontend prevention:** Ideally, prevent users from abandoning empty conversations, but backend handles it gracefully

## Configuration

### Environment Variables

**Backend (`backend/.env.local`):**
```bash
# Brain endpoints
LOCAL_BRAIN_ENDPOINT_URL=http://127.0.0.1:8001  # Local development
BRAIN_ENDPOINT_URL=https://your-brain-api.example.com  # Production (direct HTTP)

# Sync operation timeouts (seconds) - Set high to accommodate LLM processing
MEMORY_GENERATION_TIMEOUT=120  # 2 minutes
PERSONA_GENERATION_TIMEOUT=120  # 2 minutes
OPENING_MESSAGE_TIMEOUT=120  # 2 minutes

# Feature flags
ENABLE_AI_FIRST_MESSAGE=true
ENABLE_VISIT_BASED_PROMPTS=true
ENABLE_CONDITIONAL_SIDEBAR=true
```

### Feature Flags & Settings

Allow gradual rollout and easy configuration:

```python
# backend/src/config/settings.py
class Settings(BaseSettings):
    # Feature flags
    enable_ai_first_message: bool = True
    enable_visit_based_prompts: bool = True
    enable_conditional_sidebar: bool = True
    
    # Timeout settings (seconds)
    memory_generation_timeout: int = 120  # 2 minutes
    persona_generation_timeout: int = 120  # 2 minutes
    opening_message_timeout: int = 120  # 2 minutes
    
    # API Gateway / Lambda timeout should be set higher than these values
    # Recommended: 150 seconds (2.5 minutes) to allow for retries
    
    class Config:
        env_file = ".env.local"
        case_sensitive = False
```

**Important:** Ensure AWS infrastructure timeouts are configured higher than backend timeouts:
- **API Gateway timeout:** 150 seconds (configure via Terraform)
- **Lambda timeout:** 180 seconds (3 minutes, configure via Terraform)
- **Database connection timeout:** Keep default or increase if needed

## Testing Checklist

### Backend
- [ ] Visit number calculation correct for new users
- [ ] Visit number calculation correct for existing users
- [ ] Unique constraint prevents duplicate visit numbers (race condition test)
- [ ] Race condition retry logic works correctly
- [ ] Sync memory generation blocks and completes
- [ ] Sync memory generation with retry works (2 retries)
- [ ] Sync persona generation blocks and completes
- [ ] Sync persona generation with retry works (2 retries)
- [ ] Persona generation ensures memories exist first (3+ conversations with messages)
- [ ] Correct prompt selected based on visit via `prompt_purpose` column
- [ ] Prompt purpose filtering works (not name-based)
- [ ] Opening message generation and callback works
- [ ] Opening message idempotency check prevents duplicates
- [ ] Opening message uses direct HTTP even in production
- [ ] Previous memories fetched correctly (excluding current conversation)
- [ ] Empty conversations skipped during memory generation
- [ ] Visit 3 generates memories for conversations 1 AND 2
- [ ] Persona only generated for users with 3+ conversations with messages
- [ ] Timeout handling: conversation deleted and HTTP 503 returned
- [ ] Memory generation failure: conversation deleted and error returned
- [ ] Persona generation failure: conversation deleted and error returned
- [ ] Opening message timeout: conversation deleted and error returned
- [ ] Visit 4+ with <3 conversations with messages: HTTP 503 error
- [ ] Title auto-generated from user's first message
- [ ] `preparation_status` returned correctly in conversation creation
- [ ] `requires_opening_message` flag returned correctly
- [ ] Backfill script correctly assigns visit numbers chronologically
- [ ] `GET /api/conversations/{id}` includes visit_number in response
- [ ] `GET /api/conversations` includes visit_number for each conversation

### Brain
- [ ] `{{PREVIOUS_CONVERSATIONS_MEMORY}}` placeholder detected and replaced
- [ ] Previous memories formatted correctly as numbered list
- [ ] Persona placeholders still work (`{{USER_PERSONA}}`)
- [ ] Opening message endpoint generates appropriate content
- [ ] Memory generation respects message count (skips empty conversations)
- [ ] Persona generation checks conversation count >= 3
- [ ] Opening message endpoint handles missing memories gracefully

### Frontend
- [ ] Sidebar hidden for visit 1, 2, 3
- [ ] Sidebar visible for visit 4+
- [ ] AI opening message displays before user input
- [ ] User input disabled until opening message loads
- [ ] Loading states based on `preparation_status`:
  - [ ] "Reviewing your previous conversations..." for generating_memory
  - [ ] "Understanding your learning style..." for generating_persona
  - [ ] "Your coach is preparing to meet you..." for ready
- [ ] User can respond after opening message loads
- [ ] Visit number included in conversation list and detail responses
- [ ] Title updates after user's first message (from "New Chat")
- [ ] Error handling for conversation creation failures (HTTP 503)
- [ ] Error messages displayed to user when preparation fails
- [ ] Prompt manager includes `prompt_purpose` dropdown field
- [ ] Prompt manager allows setting purpose: visit_1, visit_2, visit_3, steady_state, general, or null
- [ ] Conversation creation can take 30-60s, UI shows appropriate progress

### E2E
- [ ] Complete flow: Sign up → Visit 1 (AI greets, no sidebar) → Send message → Exit
- [ ] Return visit: Visit 2 (memory generated for conv 1, injected, no sidebar) → Exit
- [ ] Visit 3: Memories from conversations 1 and 2 injected, no sidebar
- [ ] Visit 4: Persona generated (3 completed conversations), sidebar appears
- [ ] Visit 5+: Same as visit 4 behavior (steady state)
- [ ] Concurrent conversation creation doesn't create duplicate visit numbers
- [ ] Empty first conversation doesn't break visit 2
- [ ] Timeout scenarios return fallback messages/data
- [ ] Title auto-generation from first user message works

## Success Metrics

- Visit 1 completion rate (user sends at least 1 message after AI greeting)
- Visit 2 return rate (users who complete visit 1 and return)
- Memory injection success rate (memories present when needed)
- Persona generation success rate (personas exist for 4+ visit users)
- Opening message generation latency (target < 5s)
- Sync operation timeout rate (target < 1%)

## Future Enhancements

- Dynamic prompt selection based on user performance/engagement
- Adaptive visit milestones (e.g., visit 2 at different thresholds)
- Multi-dimensional persona with more than just `persona` field
- Previous memory summarization if user has 10+ conversations
- A/B testing framework for different onboarding prompts
- LLM-based title generation instead of simple first-sentence extraction
- Real-time websockets for opening message delivery (instead of polling)

---

## Document Change Summary

This document has been updated with the following critical fixes and enhancements based on comprehensive review:

### Critical Issues Fixed
1. **Visit 3 memory generation** - Now generates memories for ALL previous conversations, not just visit 2
2. **Empty conversation checks** - Added `has_messages()` validation before memory generation
3. **Synchronous opening messages** - Direct HTTP to Brain even in production (no SQS for opening messages)
4. **Race condition protection** - Unique constraint on `(user_id, visit_number)` with retry logic (simpler than transaction locks)
5. **Persona generation memory dependencies** - Ensures memories exist for 3+ conversations before generating persona
6. **Backfill logic** - Complete implementation for existing conversations
7. **Opening message idempotency** - Brain checks if message exists before generating (prevents duplicates on retry)

### Error Handling Strategy Changed
**Fail-Hard Approach Implemented:**
- Memory generation failure → Delete conversation, return HTTP 503 error
- Persona generation failure → Delete conversation, return HTTP 503 error  
- Opening message timeout → Delete conversation, return HTTP 503 error
- Visit 4+ with <3 conversations → Delete conversation, return HTTP 503 error
- No fallback messages or generic prompts used
- User sees clear error message and must retry

### Prompt Management Updates
1. **Prompt purpose filtering** - Queries by `prompt_purpose` value, not by name
2. **Flexible naming** - Prompt names can be anything, purpose determines usage
3. **Frontend prompt manager** - Added `prompt_purpose` dropdown (visit_1, visit_2, visit_3, steady_state, general)
4. **Database support** - `prompt_purpose` column with index for efficient querying
5. **Backend CRUD endpoints** - Full support for creating/updating prompts with `prompt_purpose`

### Enhancements Added (Latest Update)
1. **Retry logic** - Exponential backoff for sync memory and persona generation (2 retries)
2. **Progress indicators** - `preparation_status` field for frontend loading states
3. **Comprehensive logging** - Monitoring at all key decision points with structured logging
4. **Title auto-generation** - From user's first message instead of creation time
5. **Visit number in responses** - Added to `GET /api/conversations` and `GET /api/conversations/{id}`
6. **Timeout values increased** - All sync operations now use 120s (2 minutes) timeout
7. **Infrastructure timeout guidance** - API Gateway (150s) and Lambda (180s) recommendations added
8. **Feature flags** - Added settings for gradual rollout and easy testing
9. **Health check endpoint** - `/health/onboarding` validates system readiness
10. **Metrics instrumentation** - Comprehensive duration tracking for all operations
11. **Alembic migration** - Complete migration file with upgrade/downgrade paths
12. **Pipeline data for opening messages** - Opening messages now save pipeline_data for debugging

### New Backend Endpoints Added
1. `GET /api/internal/conversations/{conversation_id}/prompt` - Fetch prompt for opening message generation
2. `GET /api/internal/users/{user_id}/previous-memories` - Fetch previous conversation memories
3. `POST /api/internal/opening_message` - Callback endpoint for Brain's opening message
4. `GET /api/prompts/by-purpose/{purpose}` - Query prompts by purpose
5. `GET /health/onboarding` - Health check for onboarding system

### Brain Service Updates
1. **New APIService methods:**
   - `get_conversation_prompt(conversation_id)` - Fetch conversation's assigned prompt
   - `get_previous_memories(user_id, exclude_conversation_id)` - Fetch previous memories
2. **Opening message generation** - Uses conversation's assigned visit-based prompt directly
3. **Pipeline data tracking** - Opening messages include context flags (had_persona, had_previous_memories)

### Implementation Simplifications
1. **Race condition handling** - Unique constraint instead of transaction locks (simpler, non-blocking)
2. **Conversation cleanup** - Automatic deletion on preparation failure (no orphaned conversations)
3. **Error propagation** - Clear HTTP 503 errors instead of silent fallbacks
4. **Opening message prompt** - Uses same visit-based prompts, no separate template needed

### Clarifications Provided
1. **Active/production versions** - Onboarding prompts support both for A/B testing
2. **{{CONVERSATION_MEMORY}} removal** - Not used in onboarding prompts (only internal for persona generation)
3. **Visit number immutability** - Persists even after conversation deletion
4. **Frontend loading states** - Different messages for memory/persona generation phases (up to 2 minutes possible)
5. **Memory injection verbosity** - Only for first 3 visits, so no concerns about token limits
6. **Timeout configuration** - Backend operations: 120s, API Gateway: 150s, Lambda: 180s
7. **Opening message implementation** - Uses visit-based prompts directly, designed to produce welcoming first message

### Documentation Structure
- **Design Decisions & Critical Fixes** section added at top with 14 documented decisions
- **Alembic Migration** section with complete migration file
- **Metrics & Monitoring** section with instrumentation and health check
- **Prompt Management** section updated with purpose-based querying and CRUD operations
- **Helper Functions** expanded with complete implementations and error handling
- **Edge Cases & Error Handling** greatly expanded with fail-hard strategy and 120s timeouts
- **Testing Checklist** enhanced with 50+ test cases across backend, brain, frontend, and E2E
- **Frontend sections** added for prompt manager UI updates with visual indicators
- **Environment Variables** updated with 120s timeouts and feature flags
- **Configuration** section added with Settings class and infrastructure timeout requirements

---

## Recent Implementation Updates (October 2025)

### Phase 1: Critical Bug Fixes
1. **Brain Import Fix** - Added missing `OpeningMessageRequest` import to `Brain/src/main.py` (was causing 422 errors)
2. **Production Version Setup** - Created script to set all 4 onboarding prompts (`visit_1`, `visit_2`, `visit_3`, `steady_state`) as production versions
3. **Prompt Creation** - Successfully created all 4 onboarding prompts with appropriate `prompt_purpose` values via UI

### Phase 2: Auto-Conversation Creation on Login
**Problem:** Users saw empty homepage briefly before sidebar hid, creating jarring UX.

**Solution:** 
- Modified `fetchConversations()` in `ChatContext.tsx` to detect new users (0 conversations)
- Auto-creates first conversation immediately on login
- Adds new state: `isInitializingForNewUser` to show loading screen during setup
- Inline conversation creation logic to avoid circular dependencies

**Implementation:**
```typescript
// In fetchConversations()
if (fetchedConversations.length === 0) {
  setIsInitializingForNewUser(true);
  const response = await createConversation("New Chat");
  // Sets visit number, prompt version, displays AI opening message
  setIsInitializingForNewUser(false);
}
```

### Phase 3: Smooth Loading Experience
**New Component:** `ChatInterface.tsx` now shows loading screen for new users

**Features:**
- Animated star icon with pulse and ping effects
- Welcome message: "Welcome to Curiosity Coach!"
- Loading message: "Your personal learning companion is preparing to meet you..."
- Three bouncing dots animation
- Only shows during `isInitializingForNewUser` state

**Flow:**
1. User logs in → Immediately see loading screen (no empty homepage flash)
2. Backend creates conversation + generates opening message
3. Smooth transition to chat with AI greeting visible
4. Sidebar hidden from start, clean full-width layout

### Phase 4: Layout Fixes
**Problem:** Chat bubbles and input box misaligned when sidebar was hidden.

**Fixes:**
1. **ChatMessage.tsx:**
   - Changed `px-1 sm:px-0` → `px-4 sm:px-6 lg:px-8` for consistent padding
   - Updated max-widths: `max-w-[85%] sm:max-w-xs lg:max-w-md` → `max-w-[75%] sm:max-w-md lg:max-w-lg`
   - Removed conditional margin variables

2. **MessageInput.tsx:**
   - Added `shouldShowSidebar` prop
   - Made sidebar offset conditional: `lg:left-72` only when sidebar shown, `left-0` otherwise
   - Changed from fixed CSS class to dynamic conditional class

3. **ChatInterface.tsx:**
   - Main content uses `w-full` when sidebar hidden (visits 1-3)
   - Uses `flex-1` when sidebar shown (visit 4+)
   - Passes `shouldShowSidebar` to MessageInput component

### Phase 5: Debug Info Panel
**New Component:** `DebugInfo.tsx` - Floating debug panel for development

**Features:**
- Only visible when `?debug=true` in URL
- Fixed position top-right corner
- Dark themed with monospace font
- Shows:
  - **Visit Number** (1, 2, 3, or 4+) in green
  - **Prompt Purpose** (e.g., "visit_1 (First Time User)") in blue
  - **Prompt Version ID** (database ID) in purple

**Implementation:**
- Added `currentPromptVersionId` state to ChatContext
- Tracks prompt version when creating/selecting conversations
- Updates TypeScript types to include `prompt_version_id` in Conversation interface
- Conditionally renders based on `isDebugMode` from URL params

### Phase 6: Query Parameter Preservation
**Problem:** `?debug=true` was lost during login redirect.

**Fixes:**
1. **Login.tsx:**
   ```typescript
   const location = useLocation();
   const queryParams = new URLSearchParams(location.search);
   const targetPath = queryParams.toString() ? `/chat?${queryParams.toString()}` : '/chat';
   navigate(targetPath);
   ```

2. **App.tsx (ProtectedRoute):**
   ```typescript
   const location = useLocation();
   if (!user) {
     const targetPath = location.search ? `/${location.search}` : '/';
     return <Navigate to={targetPath} replace />;
   }
   ```

**Result:** Query params now preserved through entire auth flow.

### Files Modified Summary
- `Brain/src/main.py` - Fixed import, removed redundant inner import
- `curiosity-coach-frontend/src/context/ChatContext.tsx` - Auto-conversation creation, loading state, prompt version tracking
- `curiosity-coach-frontend/src/components/ChatInterface/ChatInterface.tsx` - Loading screen, debug info, layout fixes
- `curiosity-coach-frontend/src/components/ChatInterface/MessageInput.tsx` - Conditional sidebar offset
- `curiosity-coach-frontend/src/components/ChatMessage.tsx` - Proper padding and spacing
- `curiosity-coach-frontend/src/components/DebugInfo.tsx` - NEW FILE: Debug panel component
- `curiosity-coach-frontend/src/components/Login.tsx` - Query param preservation
- `curiosity-coach-frontend/src/App.tsx` - Query param preservation in protected routes
- `curiosity-coach-frontend/src/types/index.ts` - Added `prompt_version_id` to Conversation interface

### Production Readiness Status
✅ **Completed:**
- All 4 onboarding prompts created with production versions
- Auto-conversation creation for new users
- Smooth loading experience with progress indicators
- Layout properly handles sidebar show/hide
- Debug panel for development/testing
- Query parameters preserved through navigation

⚠️ **Remaining for Production:**
- E2E testing for all visit types (1, 2, 3, 4+)
- Monitoring and metrics collection
- Staging environment validation
- Documentation updates for runbooks

