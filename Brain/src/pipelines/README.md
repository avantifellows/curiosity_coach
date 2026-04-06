# Pipeline Guide

This folder is where Brain systems live.

A "pipeline" here means:

- which prompt family gets used
- which extra steps run after the first draft
- what state from the previous turn gets fed back in

Examples already in this folder:

- [legacy.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/legacy.py)
- [single_prompt.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/single_prompt.py)
- [double_prompt.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/double_prompt.py)

## The mental model

Think of Brain as two layers:

1. Common orchestration in `main.py`
2. Pipeline-specific behavior in this folder

`main.py` still does shared work like:

- fetching conversation history
- loading the conversation's assigned pipeline key
- resolving prompt context
- building `TurnExecutionContext`
- calling optional pre-generation pipeline prep
- running the base first-pass generation
- calling the selected pipeline file

The pipeline file then decides:

- keep the first draft as-is
- rewrite it
- run controller logic
- run evaluation logic
- add extra prompt passes

So a pipeline is not "the whole app".
It is the part that changes how a turn is handled.

The real lifecycle is:

1. `resolve_prompt_context(...)`
2. optional `resolve_opening_prompt_context(...)`
3. optional `prepare_turn(...)`
4. base response generation
5. `execute_turn(...)`

The opening hook matters for systems that want normal turns and opening messages to use different prompts.
The pre-generation hook matters for systems like `intent_router` that need to do routing before the final reply prompt runs.

## The core rule

`pipeline key in DB == python file name here`

Examples:

- `legacy` -> [legacy.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/legacy.py)
- `single_prompt` -> [single_prompt.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/single_prompt.py)
- `double_prompt` -> [double_prompt.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/double_prompt.py)

There is no registry to edit.
Brain imports the file dynamically in [__init__.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/__init__.py).

## What each existing pipeline does

### `legacy`

Serially, the turn looks like this:

1. Common base response generation runs first
2. Common steps may run
   - currently this includes core theme extraction on the trigger turn
3. Chat controller may rewrite the answer
4. 13-year-old rewrite may run
   - skipped in `try` mode
5. Exploration directions evaluation runs
6. Curiosity score / tip / directions get saved into pipeline data

So `legacy` is the heavy, multi-step stack.

Relevant file:
- [legacy.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/legacy.py)

### `single_prompt`

Serially, the turn looks like this:

1. Common base response generation runs first
2. Common steps may run
   - currently this still includes core theme extraction on the trigger turn
3. Stop

So `single_prompt` is much lighter than `legacy`, but not absolutely zero-overhead.
It still shares the common Brain orchestration and currently still allows common steps.

Relevant file:
- [single_prompt.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/single_prompt.py)

### `double_prompt`

Serially, the turn looks like this:

1. Common base response generation runs first
2. Common steps may run
3. If `SECOND_PROMPT_NAME_OVERRIDE` is set:
   - run a second prompt pass using the first draft as input
   - replace the final response with the refined response
   - save a `double_prompt_refinement` step
4. If no second prompt is configured:
   - no-op

So `double_prompt` is an example of "take the normal first answer, then refine it with another prompt".

Relevant file:
- [double_prompt.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/double_prompt.py)

### `intent_router`

- `main.py` builds `TurnExecutionContext`
- common code fetches:
  - conversation history
  - prompt assignment
  - persona
  - previous exploration directions
- `resolve_prompt_context(...)` swaps the normal turn prompt to `intent_response`
- `resolve_opening_prompt_context(...)` keeps opening messages on the visit prompt
- `prepare_turn(...)` fetches `intent_router`
- `prepare_turn(...)` fills router placeholders with:
  - `{{QUERY}}` from current user input
  - `{{CONVERSATION_HISTORY}}` from `turn_context.conversation_history`
  - `{{USER_PERSONA...}}` from `turn_context.user_persona`
  - `{{CORE_THEME...}}` from `turn_context.core_theme`
- `prepare_turn(...)` runs the router LLM call
- `prepare_turn(...)` parses router JSON
- `prepare_turn(...)` injects `{{INTENT_*}}` fields into `intent_response`
- base response generation runs next
- common response formatting then fills:
  - `{{QUERY}}`
  - `{{CONVERSATION_HISTORY}}`
  - `{{USER_PERSONA...}}`
  - `{{CORE_THEME...}}`
  - curiosity score placeholder if present
- `execute_turn(...)` saves the router decision into pipeline steps

## How previous state gets fed back in

Different pipelines can feed back different things.

Example: `legacy`

- previous exploration directions are extracted from prior saved pipeline data in [main.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/main.py#L346)
- they are stored on `turn_context.previous_exploration_directions` in [main.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/main.py#L490)
- `legacy.py` passes them into `chat_controller` in [legacy.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/legacy.py#L49)

`single_prompt` and `double_prompt` currently do not use that field.

## What it takes to invent a new pipeline

Usually the thinking is:

1. What is the first-pass prompt?
   - conversation-assigned prompt
   - one hardcoded prompt
   - a special prompt family

2. After the first draft, what should happen?
   - nothing
   - rewrite
   - controller
   - score/evaluate
   - second prompt pass

3. What state from previous turns matters?
   - none
   - previous exploration directions
   - conversation memory
   - persona
   - core theme

4. Which parts are shared vs unique?
   - if it is unique, keep it in that pipeline file
   - if multiple pipelines need it, move it into [common.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/common.py)

That is the real design effort.

## The pipeline contract

Every pipeline file should expose:

```py
async def resolve_prompt_context(
    *,
    prompt_context: PromptExecutionContext,
) -> PromptExecutionContext:
    ...


async def execute_turn(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    ...
```

A pipeline may also expose:

```py
async def resolve_opening_prompt_context(
    *,
    prompt_context: PromptExecutionContext,
) -> PromptExecutionContext:
    ...
```

and/or:

```py
async def prepare_turn(
    *,
    message: Any,
    turn_context: TurnExecutionContext,
    user_input: str,
) -> TurnExecutionContext:
    ...
```

### `resolve_prompt_context(...)`

Use this if the pipeline wants to:

- reuse the conversation-assigned prompt
- pin itself to one prompt from the prompt UI
- swap prompt families

### `resolve_opening_prompt_context(...)`

Use this if the pipeline wants opening messages to behave differently from normal turns.

Typical use:

- keep the normal visit prompt for openings
- but use a custom system prompt for regular turn generation

If this function is not present, Brain falls back to `resolve_prompt_context(...)` for openings too.

### `execute_turn(...)`

Use this if the pipeline wants to:

- do nothing
- rewrite the first draft
- run a second prompt
- run chat control
- run evaluations
- append extra pipeline steps

### `prepare_turn(...)`

Use this if the pipeline needs to do something before the main reply is generated.

This is for systems like:

- `intent_router`
- route-then-respond
- classify-then-prompt
- choose-one-of-many-prompts first

Typical uses:

- run a routing/classification prompt
- inspect history and set per-turn state
- replace `turn_context.prompt_context`
- inject extra placeholders into the final response prompt

## Minimal file skeleton

```py
from typing import Any, Optional

from src.core.turn_context import PromptExecutionContext, TurnExecutionContext
from src.schemas import ProcessQueryResponse
from src.services.api_service import api_service


PROMPT_NAME_OVERRIDE: Optional[str] = None


async def resolve_prompt_context(
    *,
    prompt_context: PromptExecutionContext,
) -> PromptExecutionContext:
    if not PROMPT_NAME_OVERRIDE:
        return prompt_context

    prompt_template = await api_service.get_prompt_template(
        PROMPT_NAME_OVERRIDE,
        prefer_production=False,
    )
    if not prompt_template:
        return prompt_context

    return PromptExecutionContext(
        prompt_template=prompt_template,
        prompt_name=PROMPT_NAME_OVERRIDE,
        prompt_version=None,
        prompt_purpose=None,
        prompt_id=None,
    )


async def resolve_opening_prompt_context(
    *,
    prompt_context: PromptExecutionContext,
) -> PromptExecutionContext:
    return prompt_context


async def prepare_turn(
    *,
    message: Any,
    turn_context: TurnExecutionContext,
    user_input: str,
) -> TurnExecutionContext:
    return turn_context


async def execute_turn(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    return current_curiosity_score
```

## How to add a new system

1. Create a new file here, for example `my_variant.py`
2. Implement `resolve_prompt_context(...)`
3. If needed, implement `resolve_opening_prompt_context(...)`
4. If needed, implement `prepare_turn(...)`
5. Implement `execute_turn(...)`
6. Set the user default in DB:

```sql
update users
set default_pipeline_key = 'my_variant'
where id = 284;
```

7. Start a new conversation

That is enough.

You do not add a registry import anywhere else.
Only import helpers inside your new file if you use them.

## Which file should I copy?

- Copy [single_prompt.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/single_prompt.py) if you want a prompt-first system
- Copy [legacy.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/legacy.py) if you want the current multi-step stack
- Copy [double_prompt.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/double_prompt.py) if you want a second-pass refinement system

## Active vs production

For experiments in this folder, default to:

```py
prefer_production=False
```

That means:

- Brain reads the currently active prompt version from the prompt UI
- prompt edits show up quickly in developer testing

Use production only if you are intentionally testing the stable production version.

## Common helpers

Reusable helpers live in [common.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/common.py).

Examples:

- `run_common_steps(...)`
- `append_pipeline_step(...)`
- `ensure_pipeline_metadata(...)`
- `build_history_with_latest_turn(...)`
- `normalize_pipeline_key(...)`

Add to `common.py` only when multiple pipelines need the same logic.

## Final practical advice

- If a system is under active evaluation, keep it stable. Do not turn it into a scaffold.
- If you want a new experiment, create a new file instead of mutating `legacy.py` or `single_prompt.py`.
- Keep the first version of a new pipeline small.
- A good first custom pipeline is usually one of:
  - prompt-only
  - prompt + one rewrite pass
  - prompt + one evaluator
