from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.user_personas import crud, schemas

router = APIRouter(
    prefix="/api/user-personas",
    tags=["user-personas"],
    responses={404: {"description": "Not found"}},
)

@router.post("", response_model=schemas.UserPersona)
def create_or_update_persona_endpoint(
    persona: schemas.UserPersonaCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user persona or update an existing one based on user_id.
    This endpoint is intended to be called by the Brain service.
    """
    return crud.create_or_update_user_persona(db=db, persona=persona) 