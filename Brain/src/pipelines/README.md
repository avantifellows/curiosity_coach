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
- [intent_router.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/intent_router.py)
- [intent_legacy.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/intent_legacy.py)

## The mental model

Think of Brain as two layers:

1. Common orchestration in `main.py`
2. Pipeline-specific behavior in this folder

`main.py` still does shared work like:

- fetching conversation history
- loading the conversation's assigned pipeline key
- resolving prompt context
- building `TurnExecutionContext`
- rendering shared prompt placeholders
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

1. turn prompt policy resolution
2. optional opening prompt policy resolution
3. optional `prepare_turn(...)`
4. base response generation
5. `execute_turn(...)`

Shared placeholder rendering happens in one place now.
The opening hook still matters for systems that want normal turns and opening messages to use different prompts.
The pre-generation hook still matters for systems like `intent_router` that need to do routing before the final reply prompt runs.
Shared router helpers live in [intent_support.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/pipelines/intent_support.py) so router-based pipelines do not have to duplicate LLM calling, JSON parsing, and trace-step building.

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
  - user name
  - user created_at
  - core theme
  - previous exploration directions
- turn prompt policy swaps the normal turn prompt to `intent_response`
- opening prompt policy keeps opening messages on the visit prompt
- `prepare_turn(...)` fetches `intent_router`
- `prepare_turn(...)` uses the shared renderer for router prompt placeholders
- `prepare_turn(...)` runs the router LLM call
- `prepare_turn(...)` parses router JSON
- `prepare_turn(...)` injects `{{INTENT_*}}` fields into `intent_response`
- base response generation runs next
- common response rendering then fills all standard placeholders
- `execute_turn(...)` saves the router decision into pipeline steps before the response step

### `intent_legacy`

- opening prompt stays on the assigned visit / steady-state prompt
- turn prompt also stays on the assigned visit / steady-state prompt
- `prepare_turn(...)` runs `intent_router`
- `prepare_turn(...)` injects a soft routing guidance block only on corrective turns
- base response generation runs on that guided assigned prompt
- `execute_turn(...)` saves the router step first
- `execute_turn(...)` then reuses the full legacy post-processing stack
- on real repair turns, the final trailing coach question is stripped back out

This is the easiest way to try "intent on top of legacy" without rewriting the visit prompts first.

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

Every pipeline file must expose:

```py
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

And a pipeline may declare prompt policies instead of writing resolver functions:

```py
from src.pipelines.common import ASSIGNED_PROMPT, named_prompt

TURN_PROMPT_POLICY = named_prompt("intent_response", prefer_production=False)
OPENING_PROMPT_POLICY = ASSIGNED_PROMPT
```

If the policy model is not enough, a pipeline can still expose custom resolver functions:

- `resolve_prompt_context(...)`
- `resolve_opening_prompt_context(...)`

### `TURN_PROMPT_POLICY`

Use this for most pipelines.

- `ASSIGNED_PROMPT` means use the conversation-assigned prompt
- `named_prompt("foo", prefer_production=False)` means pin the turn to one DB prompt
- if you do not define a turn policy, Brain falls back to the conversation-assigned prompt

### `resolve_opening_prompt_context(...)`

Use this if the pipeline wants opening messages to behave differently from normal turns.

Typical use:

- keep the normal visit prompt for openings
- but use a custom system prompt for regular turn generation

If this function is not present, Brain uses `OPENING_PROMPT_POLICY` if defined.
If neither is present, Brain falls back to the turn prompt policy.

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

### Shared rendering

Use the shared renderer instead of hand-writing `.replace(...)` chains.

File:
- [prompt_renderer.py](/Users/surya/may2022/avanti_code/curiosity_coach/Brain/src/core/prompt_renderer.py)

What it already knows how to inject:
- `{{QUERY}}`
- `{{CONVERSATION_HISTORY}}`
- `{{CURRENT_CURIOSITY_SCORE}}`
- `{{PREVIOUS_CONVERSATIONS_MEMORY...}}`
- `{{USER_PERSONA...}}`
- `{{CORE_THEME...}}`
- `{{CONVERSATION_MEMORY...}}`
- `{{USER_ID}}`
- `{{USER_CREATED_AT}}`
- `{{USER_NAME}}`
- `{{NAME}}`

## Minimal file skeleton

```py
from typing import Any

from src.core.turn_context import TurnExecutionContext
from src.schemas import ProcessQueryResponse

from src.pipelines.common import ASSIGNED_PROMPT, named_prompt

TURN_PROMPT_POLICY = ASSIGNED_PROMPT
# TURN_PROMPT_POLICY = named_prompt("my_prompt", prefer_production=False)

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
2. Set `TURN_PROMPT_POLICY`
3. If needed, set `OPENING_PROMPT_POLICY`
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
