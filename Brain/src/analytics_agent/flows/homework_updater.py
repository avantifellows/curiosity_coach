import json
import asyncio
from typing import List, Dict, Any
import logging
from src.services.llm_service import LLMService
from src.services.api_service import api_service

logger = logging.getLogger(__name__)

def _format_history(history: List[Dict[str, Any]]) -> str:
    return "\n".join([f"{'User' if m['is_user'] else 'AI'}: {m['content']}" for m in history])

async def run(conversation_id: int) -> None:
    history = await api_service.get_conversation_history(conversation_id)
    if not history:
        return

    pv = await api_service.get_production_prompt_version("lm_homework_updater")
    prompt_text = pv.get("prompt_text", "")
    if not prompt_text:
        return

    final_prompt = prompt_text.replace("{{CONVERSATION_HISTORY}}", _format_history(history))

    llm = LLMService()
    response_dict = await asyncio.to_thread(llm.generate_response, final_prompt, "homework_updater", True)
    raw = response_dict.get("raw_response", "")
    try:
        items = json.loads(raw)["cliffhangers in conversation"]
        temp_dict = [{"content": item} for item in items]
        if isinstance(items, list) and items:
            await api_service.post_generic_flow_items("homework", conversation_id, temp_dict)
    except Exception as e:
        logger.warning("Error parsing homework updater response", exc_info=e)
        return
