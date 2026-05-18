"""
Resolve chapter-scoped chat intent from kb_source sections and user subscription.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from src.models import KBSource, Section, UserKbSourceSubscription

CORE_CHAT_THEME_MAX_LEN = 12000


class ChapterIntentKind(str, Enum):
    ACTIVE = "active"
    CHAPTER_COMPLETE = "chapter_complete"
    NOT_SUBSCRIBED = "not_subscribed"
    NO_UNITS = "no_units"
    SOURCE_NOT_FOUND = "source_not_found"
    SECTION_NOT_FOUND = "section_not_found"


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


def _format_question_list(raw_questions: Any) -> str:
    if not isinstance(raw_questions, list):
        return ""

    cleaned: List[str] = []
    for question in raw_questions:
        if isinstance(question, str):
            text = question.strip()
        else:
            text = str(question).strip()
        if text:
            cleaned.append(text)

    if not cleaned:
        return ""
    return "\n".join(f"- {question}" for question in cleaned)


def build_core_chat_theme(
    *,
    source_title: str,
    section_title: str,
    section_order: int,
    section_focus: str,
    section_questions: Any,
) -> str:
    source = (source_title or "").strip()
    t = (section_title or "").strip()
    f = (section_focus or "").strip()
    questions = _format_question_list(section_questions)

    parts: List[str] = []
    if source:
        parts.append(f"Project source:\n{source}")
    if t:
        parts.append(f"Section:\n{t}")
    if section_order:
        parts.append(f"Section order:\n{section_order}")
    parts.append(f"Content focus:\n{f}")
    if questions:
        parts.append(f"Questions and activities:\n{questions}")
    return _trim_theme("\n\n".join(parts))


def resolve_chapter_chat_intent(
    db: Session,
    user_id: int,
    kb_source_id: int,
    section_pk: Optional[int] = None,
) -> ChapterChatIntent:
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

    chosen = None
    if section_pk is not None:
        chosen = next((s for s in sections if s.id == section_pk), None)
        if chosen is None:
            return ChapterChatIntent(
                kind=ChapterIntentKind.SECTION_NOT_FOUND,
                kb_source_id=kb_source_id,
            )
    anchor = chosen if chosen is not None else sections[0]
    focus_parts = [p for p in [(anchor.section_description or "").strip(), (anchor.section_content or "").strip()] if p]
    focus = "\n\n".join(focus_parts) if focus_parts else (anchor.section_name or "").strip()

    return ChapterChatIntent(
        kind=ChapterIntentKind.ACTIVE,
        foundational_unit_id=anchor.id,
        core_chat_theme=build_core_chat_theme(
            source_title=source.file_name or "",
            section_title=anchor.section_name or "",
            section_order=anchor.section_order or 0,
            section_focus=focus,
            section_questions=anchor.section_question_list,
        ),
        kb_source_id=kb_source_id,
    )
