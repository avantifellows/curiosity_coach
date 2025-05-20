# Simplified Conversation Mode

This document explains how to use the simplified conversation mode in the Curiosity Coach system. This mode bypasses the complex multi-step pipeline and uses a single prompt approach for handling conversations, which maintains context across short responses.

## How Simplified Mode Works

In simplified mode:

1. The system uses a single LLM call with the full conversation history
2. Short follow-up responses like "yup church" are properly interpreted in context
3. All processing happens through the `simplified_conversation` step
4. The same API endpoints are used, with configuration determining the mode

## Example of Fixed Context Issue

**Problem before:**
```
User: Pope
AI: You're asking about the Pope? That's the leader of the Catholic Church. Are you curious about the Pope's role in religion, or maybe about the current Pope specifically?
User: yup church
AI: [Out of context response because "yup church" was treated as a new topic]
```

**Fixed with simplified mode:**
```
User: Pope
AI: You're asking about the Pope? That's the leader of the Catholic Church. Are you curious about the Pope's role in religion, or maybe about the current Pope specifically?
User: yup church
AI: Great! The Pope is the head of the Catholic Church and leads over a billion Catholics worldwide. He lives in Vatican City, which is actually the smallest country in the world!
```

## How to Enable/Disable Simplified Mode

### Option 1: Using the Script

We've included a utility script to enable or disable simplified mode:

```bash
# Check current status
python /Brain/scripts/set_simplified_mode.py --status

# Enable simplified mode
python /Brain/scripts/set_simplified_mode.py --enable

# Disable simplified mode (use full pipeline)
python /Brain/scripts/set_simplified_mode.py --disable
```

### Option 2: Manual Config Change

You can also edit the S3 config directly:

1. Download the current config from S3
2. Set `"use_simplified_mode": true` in the JSON
3. Upload the modified JSON back to S3

### Option 3: Forced Mode

For testing, you can set `FORCE_SIMPLIFIED_MODE = True` in `src/process_query_entrypoint.py` to override any S3 configuration.

## Technical Implementation

The simplified mode leverages:

1. New `use_simplified_mode` flag in `FlowConfig` model
2. The `simplified_conversation` step in the pipeline
3. The `simplified_conversation_prompt.txt` prompt template
4. Modified processing logic in `process_query` and `process_follow_up` functions

No changes to the frontend or API endpoints are needed, as this is all handled through the configuration. 