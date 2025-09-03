from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from typing import List
from src.internal import crud
from src.memories.schemas import MemoryInDB
from src.memories import crud as memories_crud
from src.user_personas.schemas import UserPersona as UserPersonaSchema
from src.models import UserPersona

router = APIRouter(
    prefix="/api/internal",
    tags=["internal"],
    # These endpoints should not be exposed in public docs
    include_in_schema=False,
)

@router.get("/users/{user_id}/memories", response_model=List[MemoryInDB])
def get_user_conversation_memories(user_id: int, db: Session = Depends(get_db)):
    """
    Get all conversation memories for a specific user.
    This is an internal endpoint for the Brain service.
    """
    memories = crud.get_conversation_memories_by_user_id(db=db, user_id=user_id)
    if not memories:
        # It's better to return an empty list than a 404
        # if the user exists but has no memories.
        # A 404 could imply the user or the endpoint itself was not found.
        return []
    return memories 

@router.get("/conversations/{conversation_id}/memory", response_model=MemoryInDB)
def get_conversation_memory(conversation_id: int, db: Session = Depends(get_db)):
    """
    Get the memory for a specific conversation. Returns 404 if not found.
    This is an internal endpoint for the Brain service.
    """
    memory = memories_crud.get_memory_by_conversation_id(db=db, conversation_id=conversation_id)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found for conversation")
    return memory


@router.get("/users/{user_id}/persona", response_model=UserPersonaSchema)
def get_user_persona(user_id: int, db: Session = Depends(get_db)):
    """
    Get the user persona by user_id. Returns 404 if not found.
    This is an internal endpoint for the Brain service.
    """
    persona: UserPersona | None = db.query(UserPersona).filter(UserPersona.user_id == user_id).first()
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found for user")
    return persona