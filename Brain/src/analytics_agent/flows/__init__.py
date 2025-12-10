from typing import Dict, Awaitable, Callable
from . import homework_updater
from . import knowledge_updater

FLOW_HANDLERS: Dict[str, Callable[[int], Awaitable[None]]] = {
    "lm_homework_updater": homework_updater.run,
    "lm_knowledge_updater": knowledge_updater.run,
}