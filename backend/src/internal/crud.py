from sqlalchemy.orm import Session
from src.models import Conversation, ConversationMemory, User, KBSource, Section
from typing import List, Dict, Any


def get_conversation_memories_by_user_id(db: Session, user_id: int) -> List[ConversationMemory]:
    """
    Retrieves all conversation memories for a given user ID.
    """
    return (
        db.query(ConversationMemory)
        .join(Conversation, ConversationMemory.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user_id)
        .all()
    )


def save_extracted_topics_payload(
    db: Session,
    *,
    file_name: str,
    details: str | None,
    created_by: int | None,
    sections_payload: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Persist extracted PDF payload into kb_source + sections.
    """
    kb_source = KBSource(file_name=file_name, details=details, created_by=created_by)
    db.add(kb_source)
    db.flush()

    section_ids: List[int] = []
    for item in sections_payload:
        row = Section(
            kb_source_id=kb_source.id,
            section_id=item["section_id"],
            section_name=item.get("section_name") or "",
            section_description=item.get("section_description") or "",
            section_content=item.get("section_content") or "",
            section_question_list=item.get("section_question_list") or [],
            section_order=int(item.get("section_order") or 0),
        )
        db.add(row)
        db.flush()
        section_ids.append(row.id)

    return {
        "kb_source_id": kb_source.id,
        "section_ids": section_ids,
        "section_count": len(section_ids),
    }


def get_kb_source_count_by_file_name(db: Session, file_name: str) -> int:
    return db.query(KBSource).filter(KBSource.file_name == file_name).count()
