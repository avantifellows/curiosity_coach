import json
import os
import re
from typing import Any, Dict, Optional, Tuple

import httpx

from src.services.llm_service import LLMService
from src.utils.logger import logger

PROMPT_NAME_CURIOSITY_SCORE = "curiosity_score_evaluation"


async def _get_prompt_from_backend(prompt_name: str) -> Optional[str]:
    """Fetch the active prompt template for the given prompt name."""
    backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
    url = f"{backend_url}/api/prompts/{prompt_name}/versions/active"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
            prompt_text = payload.get("prompt_text")
            if not prompt_text:
                logger.warning("Prompt '%s' response missing prompt_text", prompt_name)
            return prompt_text
    except Exception as exc:
        logger.error("Error fetching prompt %s from backend: %s", prompt_name, exc)
        return None


def _parse_curiosity_score(raw_response: str) -> Tuple[Optional[int], Optional[str]]:
    """Extract a curiosity score (0-100) and optional reason from the LLM raw response."""
    if not raw_response:
        return None, None

    raw_response = raw_response.strip()

    # Try JSON first
    try:
        parsed = json.loads(raw_response)
        if isinstance(parsed, dict):
            score = parsed.get("curiosity_score") or parsed.get("score")
            reason = parsed.get("reason") if isinstance(parsed.get("reason"), str) else None
            if isinstance(score, (int, float)):
                return int(max(0, min(100, round(score)))), reason
        elif isinstance(parsed, (int, float)):
            return int(max(0, min(100, round(parsed)))), None
    except json.JSONDecodeError:
        pass

    # Fallback: search for the last integer-looking number in the response
    matches = re.findall(r"(\d{1,3})", raw_response)
    if not matches:
        return None, None

    try:
        score = int(matches[-1])
        return max(0, min(100, score)), None
    except ValueError:
        return None, None


async def evaluate_curiosity_score(
    *,
    conversation_history: Optional[str],
    latest_user_message: str,
    latest_ai_response: str,
    current_curiosity_score: int,
    conversation_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate a curiosity score using a dedicated LLM prompt layer."""

    prompt_template = await _get_prompt_from_backend(PROMPT_NAME_CURIOSITY_SCORE)
    if not prompt_template:
        return {
            "prompt": None,
            "raw_response": None,
            "curiosity_score": None,
            "applied": False,
            "error": "Prompt not found",
        }

    history_block = conversation_history or "No previous conversation."
    prompt = (
        prompt_template.replace("{{CONVERSATION_HISTORY}}", history_block)
        .replace("{{LATEST_USER_MESSAGE}}", latest_user_message or "")
        .replace("{{LATEST_AI_RESPONSE}}", latest_ai_response or "")
        .replace(
            "{{CURRENT_CURIOSITY_SCORE}}",
            str(max(0, min(100, current_curiosity_score))),
        )
    )

    prompt = prompt.replace(
        "{{CONVERSATION_ID}}",
        str(conversation_id) if conversation_id is not None else "",
    )

    llm = LLMService()
    llm_response = llm.generate_response(
        final_prompt=prompt,
        call_type="curiosity_score_evaluation",
        json_mode=False,
    )

    raw_response = (llm_response or {}).get("raw_response", "")
    parsed_score, parsed_reason = _parse_curiosity_score(raw_response)

    if parsed_score is None:
        return {
            "prompt": prompt,
            "raw_response": raw_response,
            "curiosity_score": None,
            "reason": parsed_reason,
            "applied": False,
            "error": "Could not parse curiosity score",
        }

    return {
        "prompt": prompt,
        "raw_response": raw_response,
        "curiosity_score": parsed_score,
        "reason": parsed_reason,
        "applied": True,
        "error": None,
    }
