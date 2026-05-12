"""
Resolve which foundational unit anchors a chapter-scoped chat (CORE_THEME) and update progress.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.models import FoundationalUnit, KBSource, Progress, Question

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
    foundational_unit_id: Optional[int] = None
    core_chat_theme: Optional[str] = None
    kb_source_id: Optional[int] = None


SpineRow = Tuple[int, str, str]  # foundational_unit_id, question_content, fu_content


def _trim_theme(text: str) -> str:
    if len(text) <= CORE_CHAT_THEME_MAX_LEN:
        return text
    return text[: CORE_CHAT_THEME_MAX_LEN - 24] + "\n...(truncated)"


def build_core_chat_theme(question_content: str, fu_content: str) -> str:
    q = (question_content or "").strip()
    f = (fu_content or "").strip()
    parts: List[str] = []
    if q:
        parts.append(f"Question context:\n{q}")
    parts.append(f"Current foundational unit:\n{f}")
    return _trim_theme("\n\n".join(parts))


def select_intent_from_spine_and_status(
    spine: List[SpineRow],
    status_by_fu: Dict[int, str],
) -> ChapterChatIntent:
    """
    Pure selection: spine order is canonical. Requires a status entry per spine FU id.
    """
    if not spine:
        return ChapterChatIntent(kind=ChapterIntentKind.NO_UNITS)

    spine_ids = [row[0] for row in spine]
    for fu_id in spine_ids:
        if fu_id not in status_by_fu:
            return ChapterChatIntent(kind=ChapterIntentKind.NOT_SUBSCRIBED)

    for fu_id, q_c, fu_c in spine:
        if status_by_fu.get(fu_id) == "ongoing":
            return ChapterChatIntent(
                kind=ChapterIntentKind.ACTIVE,
                foundational_unit_id=fu_id,
                core_chat_theme=build_core_chat_theme(q_c, fu_c),
            )
    for fu_id, q_c, fu_c in spine:
        if status_by_fu.get(fu_id) == "not_started":
            return ChapterChatIntent(
                kind=ChapterIntentKind.ACTIVE,
                foundational_unit_id=fu_id,
                core_chat_theme=build_core_chat_theme(q_c, fu_c),
            )

    if all(status_by_fu.get(i) == "done" for i in spine_ids):
        return ChapterChatIntent(kind=ChapterIntentKind.CHAPTER_COMPLETE)

    # Unexpected statuses: fall back to first spine slot as active
    fu_id, q_c, fu_c = spine[0]
    return ChapterChatIntent(
        kind=ChapterIntentKind.ACTIVE,
        foundational_unit_id=fu_id,
        core_chat_theme=build_core_chat_theme(q_c, fu_c),
    )


def resolve_chapter_chat_intent(db: Session, user_id: int, kb_source_id: int) -> ChapterChatIntent:
    source = db.query(KBSource).filter(KBSource.id == kb_source_id).first()
    if not source:
        return ChapterChatIntent(kind=ChapterIntentKind.SOURCE_NOT_FOUND)

    rows = (
        db.query(
            FoundationalUnit.id,
            Question.content,
            FoundationalUnit.content,
        )
        .join(Question, Question.id == FoundationalUnit.question_id)
        .filter(Question.kb_source_id == kb_source_id)
        .order_by(Question.q_seq_number.asc(), FoundationalUnit.fu_seq_number.asc())
        .all()
    )
    if not rows:
        return ChapterChatIntent(
            kind=ChapterIntentKind.NO_UNITS,
            kb_source_id=kb_source_id,
        )

    spine: List[SpineRow] = [(int(r[0]), r[1] or "", r[2] or "") for r in rows]
    fu_ids = [row[0] for row in spine]

    prog_rows = (
        db.query(Progress.foundational_unit_id, Progress.status)
        .filter(
            Progress.user_id == user_id,
            Progress.foundational_unit_id.in_(fu_ids),
        )
        .all()
    )
    status_by_fu = {int(r[0]): r[1] for r in prog_rows}

    intent = select_intent_from_spine_and_status(spine, status_by_fu)
    return ChapterChatIntent(
        kind=intent.kind,
        foundational_unit_id=intent.foundational_unit_id,
        core_chat_theme=intent.core_chat_theme,
        kb_source_id=kb_source_id,
    )


def update_progress_ongoing_for_unit(
    db: Session,
    user_id: int,
    foundational_unit_id: int,
    conversation_id: int,
) -> None:
    row = (
        db.query(Progress)
        .filter(
            Progress.user_id == user_id,
            Progress.foundational_unit_id == foundational_unit_id,
        )
        .first()
    )
    if not row:
        return
    row.status = "ongoing"
    row.conversation_id = str(conversation_id)
    db.add(row)
    db.commit()
