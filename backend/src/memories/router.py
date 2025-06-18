from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.memories import crud
from src.memories.schemas import MemoryCreate, MemoryInDB

router = APIRouter(
    prefix="/api/memories",
    tags=["memories"],
    responses={404: {"description": "Not found"}},
)

@router.post("", response_model=MemoryInDB)
def upsert_memory_endpoint(
    memory: MemoryCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new memory or update an existing one based on conversation_id.
    """
    return crud.upsert_memory(db=db, memory=memory) 