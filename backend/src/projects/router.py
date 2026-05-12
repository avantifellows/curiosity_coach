from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from src.auth.dependencies import get_current_user
from src.database import get_db
from src.models import (
    User,
    KBSource,
    Question,
    FoundationalUnit,
    Progress,
)
from src.projects.progress_selection import ChapterIntentKind, resolve_chapter_chat_intent


router = APIRouter(
    prefix="/api/projects",
    tags=["projects"],
)


class ProjectSourceResponse(BaseModel):
    id: int
    file_name: str
    details: Optional[str] = None


class SubscribeProjectRequest(BaseModel):
    kb_source_id: int


class SubscribeProjectResponse(BaseModel):
    kb_source_id: int
    total_units: int
    created_count: int
    existing_count: int


class SubscribedProjectResponse(BaseModel):
    kb_source_id: int
    file_name: str


class ChapterChatIntentResponse(BaseModel):
    outcome: str
    kb_source_id: int
    foundational_unit_id: Optional[int] = None
    core_chat_theme: Optional[str] = Field(
        default=None,
        description="Prompt-oriented text when outcome is active",
    )


@router.get("/chapter-chat-intent", response_model=ChapterChatIntentResponse)
def get_chapter_chat_intent(
    kb_source_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Resolve which foundational unit should anchor the next chat for this kb source,
    or whether the chapter is already complete / user is not set up.
    """
    intent = resolve_chapter_chat_intent(db, current_user.id, kb_source_id)
    if intent.kind == ChapterIntentKind.SOURCE_NOT_FOUND:
        raise HTTPException(
            status_code=404,
            detail={"code": "source_not_found", "message": "Project source not found"},
        )

    outcome_map = {
        ChapterIntentKind.ACTIVE: "active",
        ChapterIntentKind.CHAPTER_COMPLETE: "chapter_complete",
        ChapterIntentKind.NOT_SUBSCRIBED: "not_subscribed",
        ChapterIntentKind.NO_UNITS: "no_units",
    }
    outcome = outcome_map[intent.kind]
    return ChapterChatIntentResponse(
        outcome=outcome,
        kb_source_id=kb_source_id,
        foundational_unit_id=intent.foundational_unit_id,
        core_chat_theme=intent.core_chat_theme,
    )


@router.get("/sources", response_model=List[ProjectSourceResponse])
def list_project_sources(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    sources = (
        db.query(KBSource)
        .order_by(KBSource.created_at.desc())
        .all()
    )
    return [
        ProjectSourceResponse(
            id=source.id,
            file_name=source.file_name,
            details=source.details,
        )
        for source in sources
    ]


@router.get("/subscribed", response_model=List[SubscribedProjectResponse])
def list_subscribed_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(
            KBSource.id.label("kb_source_id"),
            KBSource.file_name.label("file_name"),
        )
        .join(Question, Question.kb_source_id == KBSource.id)
        .join(FoundationalUnit, FoundationalUnit.question_id == Question.id)
        .join(Progress, Progress.foundational_unit_id == FoundationalUnit.id)
        .filter(Progress.user_id == current_user.id)
        .distinct()
        .order_by(KBSource.file_name.asc())
        .all()
    )

    return [
        SubscribedProjectResponse(
            kb_source_id=row.kb_source_id,
            file_name=row.file_name,
        )
        for row in rows
    ]


@router.post("/subscribe", response_model=SubscribeProjectResponse)
def subscribe_to_project(
    payload: SubscribeProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = db.query(KBSource).filter(KBSource.id == payload.kb_source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Project source not found")

    fu_rows = (
        db.query(FoundationalUnit.id)
        .join(Question, Question.id == FoundationalUnit.question_id)
        .filter(Question.kb_source_id == payload.kb_source_id)
        .all()
    )
    foundational_unit_ids = [row[0] for row in fu_rows]
    total_units = len(foundational_unit_ids)

    if total_units == 0:
        return SubscribeProjectResponse(
            kb_source_id=payload.kb_source_id,
            total_units=0,
            created_count=0,
            existing_count=0,
        )

    existing_rows = (
        db.query(Progress.foundational_unit_id)
        .filter(
            Progress.user_id == current_user.id,
            Progress.foundational_unit_id.in_(foundational_unit_ids),
        )
        .all()
    )
    existing_fu_ids = {row[0] for row in existing_rows}

    new_progress_rows = [
        Progress(
            user_id=current_user.id,
            foundational_unit_id=fu_id,
            conversation_id="not started",
            status="not_started",
            remarks=None,
            action_point_given=None,
            context=None,
        )
        for fu_id in foundational_unit_ids
        if fu_id not in existing_fu_ids
    ]

    if new_progress_rows:
        db.add_all(new_progress_rows)
        db.commit()

    created_count = len(new_progress_rows)
    existing_count = total_units - created_count

    return SubscribeProjectResponse(
        kb_source_id=payload.kb_source_id,
        total_units=total_units,
        created_count=created_count,
        existing_count=existing_count,
    )
