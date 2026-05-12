"""
Run fu_completion_checker (DB prompt) via Brain and update linked progress row.
"""
from __future__ import annotations

import logging
import re
from typing import Literal, Tuple

import httpx
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.models import Message, Progress, get_conversation, get_conversation_history
from src.prompts.service import PromptService

logger = logging.getLogger(__name__)

PROMPT_NAME = "fu_completion_checker"
MAX_HISTORY_CHARS = 100_000


def _format_history(messages: list[Message]) -> str:
    lines: list[str] = []
    for m in messages:
        role = "User" if m.is_user else "Assistant"
        lines.append(f"{role}: {m.content}")
    return "\n".join(lines)


def _inject_placeholders(template: str, core_theme: str, history: str) -> str:
    text = template
    text = text.replace("{{CORE_THEME}}", core_theme)
    text = text.replace("{{CONVERSATION_HISTORY}}", history)
    text = text.replace("{{COVERSATION_HISTORY}}", history)
    return text


def _parse_status(raw: str) -> Literal["ongoing", "done"]:
    s = (raw or "").strip().lower()
    matches = list(re.finditer(r"\b(done|ongoing)\b", s))
    if not matches:
        return "ongoing"
    return "done" if matches[-1].group(1) == "done" else "ongoing"


def run_fu_completion_check(db: Session, conversation_id: int) -> Tuple[str, int]:
    """
    Returns (new_status, progress_id).
    Raises ValueError for missing data / config; httpx.HTTPError for Brain failures.
    """
    conv = get_conversation(db, conversation_id)
    if not conv:
        raise ValueError("Conversation not found")

    progress_row = (
        db.query(Progress)
        .filter(
            Progress.user_id == conv.user_id,
            Progress.conversation_id == str(conversation_id),
        )
        .first()
    )
    if not progress_row:
        raise ValueError(
            "No progress record is linked to this conversation; chapter-scoped chats only."
        )

    msgs = get_conversation_history(db, conversation_id, limit=500)
    if not msgs:
        raise ValueError("Conversation has no messages to evaluate")

    prompt_service = PromptService()
    pv = prompt_service.get_production_prompt_version(db, PROMPT_NAME)
    if not pv:
        raise ValueError(
            f"Prompt '{PROMPT_NAME}' is missing or has no production/active version in the database."
        )

    history = _format_history(msgs)
    if len(history) > MAX_HISTORY_CHARS:
        history = history[:MAX_HISTORY_CHARS] + "\n...(truncated)"

    core_theme = (conv.core_chat_theme or "").strip() or "(not specified)"
    rendered = _inject_placeholders(pv.prompt_text, core_theme, history)

    brain_base = (
        settings.LOCAL_BRAIN_ENDPOINT_URL
        if settings.APP_ENV == "development"
        else settings.BRAIN_ENDPOINT_URL
    ).rstrip("/")
    url = f"{brain_base}/fu-completion-classify"

    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json={"prompt": rendered})
        resp.raise_for_status()
        data = resp.json()

    new_status = data.get("status") if isinstance(data, dict) else None
    if new_status not in ("ongoing", "done"):
        raw = data.get("raw_response", "") if isinstance(data, dict) else str(data)
        new_status = _parse_status(str(raw))

    progress_row.status = new_status
    progress_row.conversation_id = str(conversation_id)
    db.add(progress_row)
    db.commit()
    db.refresh(progress_row)

    logger.info(
        "FU completion check progress_id=%s conversation_id=%s status=%s",
        progress_row.id,
        conversation_id,
        new_status,
    )
    return new_status, progress_row.id
