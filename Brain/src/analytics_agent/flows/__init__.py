from typing import Dict, Awaitable, Callable
from . import homework_updater

FLOW_HANDLERS: Dict[str, Callable[[int], Awaitable[None]]] = {
    "lm_homework_updater": homework_updater.run,
}