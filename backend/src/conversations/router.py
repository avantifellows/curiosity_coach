from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from src.database import get_db
from src.models import User, Conversation # Assuming User model is needed for auth dependency
# TODO: Verify the correct import path and function name for auth dependency
from src.auth.dependencies import get_current_user # Use the new dependency that returns the User object
from src.conversations import schemas # Use the schemas we just created
from src import models # Import CRUD functions from models.py

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversations"],
    # dependencies=[Depends(get_current_active_user)], # Optional: Apply auth to all routes in this router
    responses={404: {"description": "Not found"}},
)

@router.get("", response_model=List[schemas.ConversationSummary])
async def list_conversations_for_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user), # Use the new dependency
    limit: int = Query(default=50, ge=1, le=200), # Add pagination
    offset: int = Query(default=0, ge=0)
):
    """
    Retrieve conversations for the authenticated user, ordered by most recently updated.
    """
    conversations = models.list_user_conversations(
        db=db, user_id=current_user.id, limit=limit, offset=offset
    )
    return conversations # Pydantic will automatically convert based on ConversationSummary schema

@router.post("", response_model=schemas.Conversation, status_code=status.HTTP_201_CREATED)
async def create_new_conversation(
    conversation_data: Optional[schemas.ConversationCreate] = None, # Allow empty body to use default title
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user), # Use the new dependency here too
):
    """
    Create a new conversation for the authenticated user.
    A title can optionally be provided in the request body.
    """
    title = conversation_data.title if conversation_data else "New Chat" # Use default if body is empty or title not provided
    
    conversation = models.create_conversation(
        db=db, user_id=current_user.id, title=title
    )
    return conversation 