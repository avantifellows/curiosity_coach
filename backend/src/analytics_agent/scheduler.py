# scheduler.py
from typing import Sequence
import httpx
from src.config.settings import settings
from .registry import flows_for_event

async def enqueue_flows(conversation_id: int, event: str, flows: Sequence[str] | None = None) -> None:
    flows: Sequence[str] = flows_for_event(event)
    if not flows:
        return
    brain = settings.LOCAL_BRAIN_ENDPOINT_URL if settings.APP_ENV == "development" else settings.BRAIN_ENDPOINT_URL
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(
            f"{brain}/tasks",
            json={
                "task_type": "RUN_LM_ANALYTICS_FLOWS",
                "conversation_id": conversation_id,
                "event": event,
                "flows": list(flows),
            },
        )