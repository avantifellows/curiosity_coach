from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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
