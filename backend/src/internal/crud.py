from sqlalchemy.orm import Session
from src.models import Conversation, ConversationMemory, User, KBSource, Question, FoundationalUnit
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
    questions_payload: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Persist extracted topic payload into kb_source/questions/foundational_unit.
    Sequence numbering is deterministic and follows payload array order.
    """
    kb_source = KBSource(file_name=file_name, details=details, created_by=created_by)
    db.add(kb_source)
    db.flush()

    question_ids: List[int] = []
    fu_count = 0

    for q_index, q_item in enumerate(questions_payload, start=1):
        question_row = Question(
            kb_source_id=kb_source.id,
            q_seq_number=q_index,
            content=q_item["question"],
        )
        db.add(question_row)
        db.flush()
        question_ids.append(question_row.id)

        for fu_index, fu_content in enumerate(q_item["foundational_units"], start=1):
            fu_row = FoundationalUnit(
                question_id=question_row.id,
                fu_seq_number=fu_index,
                content=fu_content,
            )
            db.add(fu_row)
            fu_count += 1

    return {
        "kb_source_id": kb_source.id,
        "question_ids": question_ids,
        "question_count": len(question_ids),
        "foundational_unit_count": fu_count,
    }


def get_kb_source_count_by_file_name(db: Session, file_name: str) -> int:
    return db.query(KBSource).filter(KBSource.file_name == file_name).count()