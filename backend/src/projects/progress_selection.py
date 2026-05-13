"""
Resolve chapter-scoped chat intent from kb_source sections and user subscription.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from sqlalchemy.orm import Session

from src.models import KBSource, Section, UserKbSourceSubscription

CORE_CHAT_THEME_MAX_LEN = 12000


class ChapterIntentKind(str, Enum):
    ACTIVE = "active"
    CHAPTER_COMPLETE = "chapter_complete"
    NOT_SUBSCRIBED = "not_subscribed"
    NO_UNITS = "no_units"
    SOURCE_NOT_FOUND = "source_not_found"


@dataclass
class ChapterChatIntent:
    kind: ChapterIntentKind
    foundational_unit_id: Optional[int] = None  # section PK for API compatibility
    core_chat_theme: Optional[str] = None
    kb_source_id: Optional[int] = None


def _trim_theme(text: str) -> str:
    if len(text) <= CORE_CHAT_THEME_MAX_LEN:
        return text
    return text[: CORE_CHAT_THEME_MAX_LEN - 24] + "\n...(truncated)"


def build_core_chat_theme(section_title: str, section_focus: str) -> str:
    t = (section_title or "").strip()
    f = (section_focus or "").strip()
    parts: List[str] = []
    if t:
        parts.append(f"Section:\n{t}")
    parts.append(f"Content focus:\n{f}")
    return _trim_theme("\n\n".join(parts))


def resolve_chapter_chat_intent(db: Session, user_id: int, kb_source_id: int) -> ChapterChatIntent:
    source = db.query(KBSource).filter(KBSource.id == kb_source_id).first()
    if not source:
        return ChapterChatIntent(kind=ChapterIntentKind.SOURCE_NOT_FOUND)

    subscribed = (
        db.query(UserKbSourceSubscription)
        .filter(
            UserKbSourceSubscription.user_id == user_id,
            UserKbSourceSubscription.kb_source_id == kb_source_id,
        )
        .first()
    )
    if not subscribed:
        return ChapterChatIntent(
            kind=ChapterIntentKind.NOT_SUBSCRIBED,
            kb_source_id=kb_source_id,
        )

    sections = (
        db.query(Section)
        .filter(Section.kb_source_id == kb_source_id)
        .order_by(Section.section_order.asc(), Section.id.asc())
        .all()
    )
    if not sections:
        return ChapterChatIntent(
            kind=ChapterIntentKind.NO_UNITS,
            kb_source_id=kb_source_id,
        )

    first = sections[0]
    focus_parts = [p for p in [(first.section_description or "").strip(), (first.section_content or "").strip()] if p]
    focus = "\n\n".join(focus_parts) if focus_parts else (first.section_name or "").strip()

    return ChapterChatIntent(
        kind=ChapterIntentKind.ACTIVE,
        foundational_unit_id=first.id,
        core_chat_theme=build_core_chat_theme(first.section_name or "", focus),
        kb_source_id=kb_source_id,
    )
