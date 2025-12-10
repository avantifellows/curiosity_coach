from typing import Sequence
from .flows import FLOW_HANDLERS

async def run_flows(conversation_id: int, flow_names: Sequence[str]):
    for name in flow_names:
        handler = FLOW_HANDLERS.get(name)
        if handler:
            await handler(conversation_id)