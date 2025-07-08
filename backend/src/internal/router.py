from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from typing import List
from src.internal import crud
from src.memories.schemas import MemoryInDB

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