# registry.py
MEMORY_GENERATION_EVENT = "memory_generation"

FLOW_REGISTRY = {
    MEMORY_GENERATION_EVENT: ["lm_homework_updater", "lm_knowledge_updater"],
}

def flows_for_event(event: str) -> list[str]:
    return FLOW_REGISTRY.get(event, [])