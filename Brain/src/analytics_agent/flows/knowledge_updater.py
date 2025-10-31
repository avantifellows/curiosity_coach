# Brain/src/analytics_agent/flows/knowledge_updater.py
import asyncio
from typing import Any, Dict, List
from src.services.api_service import api_service
from src.services.llm_service import LLMService

def _format_history(history: List[Dict[str, Any]]) -> str:
    return "\n".join([f"{'User' if m.get('is_user') else 'AI'}: {m.get('content','')}" for m in history])


async def run(conversation_id: int) -> None:
    history = await api_service.get_conversation_history(conversation_id)
    if not history:
        return

    pv = await api_service.get_production_prompt_version("lm_knowledge_updater")
    prompt_text = pv.get("prompt_text", "") if isinstance(pv, dict) else ""
    if not prompt_text:
        return

    final_prompt = prompt_text.replace("{{CONVERSATION_HISTORY}}", _format_history(history))

    llm = LLMService()
    response = await asyncio.to_thread(llm.generate_response, final_prompt, "knowledge_updater")
    raw = response.get("raw_response", "") if isinstance(response, dict) else ""
    print(raw)
    print(type(raw))
    print(len(raw))
    print("--------------------------------")
    if not raw:
        return

    await api_service.post_generic_flow_items("knowledge-updater", conversation_id, [{"summary": raw}])