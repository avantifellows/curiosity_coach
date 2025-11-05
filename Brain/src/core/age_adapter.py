import os
from typing import Optional
import httpx
from src.services.llm_service import LLMService
from src.utils.logger import logger

PROMPT_NAME_13YO = "generate_response_for_13_year_old"


async def _get_prompt_from_backend(prompt_name: str) -> Optional[str]:
    try:
        backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
        url = f"{backend_url}/api/prompts/{prompt_name}/versions/active"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return data.get("prompt_text", "")
    except Exception as e:
        logger.error(f"Error fetching prompt {prompt_name} from backend: {e}")
        return None


async def generate_response_for_13_year_old(current_response: str) -> dict:
    try:
        prompt_template = await _get_prompt_from_backend(PROMPT_NAME_13YO)
        if not prompt_template:
            logger.warning("13yo prompt not found; returning original response")
            return {
                "original_response": current_response,
                "simplified_response": current_response,
                "applied": False,
                "prompt": None,
                "error": "Prompt not found",
            }

        final_prompt = prompt_template.replace("{{CURRENT_RESPONSE}}", current_response)

        llm = LLMService()
        llm_resp = llm.generate_response(
            final_prompt=final_prompt, call_type="age_adapter_13yo", json_mode=False
        )
        simplified = (llm_resp or {}).get("raw_response", "").strip()
        if not simplified:
            return {
                "original_response": current_response,
                "simplified_response": current_response,
                "applied": False,
                "prompt": final_prompt,
                "error": "Empty response from LLM",
            }

        return {
            "original_response": current_response,
            "simplified_response": simplified,
            "applied": True,
            "prompt": final_prompt,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Error simplifying for 13-year-old: {e}", exc_info=True)
        return {
            "original_response": current_response,
            "simplified_response": current_response,
            "applied": False,
            "prompt": None,
            "error": str(e),
        }


