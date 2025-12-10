import os
from src.utils.logger import logger

EXPLORATION_DIRECTIONS_ENABLED = os.getenv("EXPLORATION_DIRECTIONS_ENABLED", "true").lower() == "true"
EXPLORATION_DIRECTIONS_PROMPT_NAME = "exploration_directions_evaluation"

logger.info(f"Exploration directions evaluation enabled: {EXPLORATION_DIRECTIONS_ENABLED}")