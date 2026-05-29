from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional

from src.auth.dependencies import get_current_user
from src.database import get_db
from src.models import User, KBSource, Section, UserKbSourceSubscription
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


class ProjectSectionResponse(BaseModel):
    """One curriculum section row (sections.id is the DB primary key)."""

    id: int
    section_order: int
    section_name: str
    curriculum_section_key: str = Field(
        ...,
        description="Ingest-defined key (column sections.section_id).",
    )
    description_preview: str = ""


class ChapterChatIntentResponse(BaseModel):
    outcome: str
    kb_source_id: int
    foundational_unit_id: Optional[int] = None
    core_chat_theme: Optional[str] = Field(
        default=None,
        description="Prompt-oriented text when outcome is active (section-based curriculum).",
    )


@router.get("/chapter-chat-intent", response_model=ChapterChatIntentResponse)
def get_chapter_chat_intent(
    kb_source_id: int = Query(..., ge=1),
    section_id: Optional[int] = Query(
        None,
        ge=1,
        description="Optional sections.id (DB PK) to anchor theme; defaults to first section.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Resolve which section anchors the next chat for this kb source.
    foundational_unit_id is the section row id (legacy field name for API compatibility).
    """
    intent = resolve_chapter_chat_intent(
        db, current_user.id, kb_source_id, section_pk=section_id
    )
    if intent.kind == ChapterIntentKind.SOURCE_NOT_FOUND:
        raise HTTPException(
            status_code=404,
            detail={"code": "source_not_found", "message": "Project source not found"},
        )
    if intent.kind == ChapterIntentKind.SECTION_NOT_FOUND:
        raise HTTPException(
            status_code=404,
            detail={"code": "section_not_found", "message": "That section was not found for this project."},
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
    available_only: bool = Query(
        False,
        description="If true, exclude kb sources the current user is already subscribed to.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(KBSource).order_by(KBSource.created_at.desc())
    if available_only:
        subscribed_ids = (
            db.query(UserKbSourceSubscription.kb_source_id)
            .filter(UserKbSourceSubscription.user_id == current_user.id)
            .all()
        )
        ids = [row[0] for row in subscribed_ids]
        if ids:
            q = q.filter(~KBSource.id.in_(ids))
    sources = q.all()
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
    """KB sources the current user has subscribed to."""
    rows = (
        db.query(KBSource.id.label("kb_source_id"), KBSource.file_name.label("file_name"))
        .join(
            UserKbSourceSubscription,
            UserKbSourceSubscription.kb_source_id == KBSource.id,
        )
        .filter(UserKbSourceSubscription.user_id == current_user.id)
        .order_by(UserKbSourceSubscription.created_at.asc(), KBSource.file_name.asc())
        .all()
    )

    return [
        SubscribedProjectResponse(
            kb_source_id=row.kb_source_id,
            file_name=row.file_name,
        )
        for row in rows
    ]


_SECTION_PREVIEW_MAX = 280


def _preview_text(text: str, max_len: int = _SECTION_PREVIEW_MAX) -> str:
    t = (text or "").strip().replace("\r\n", "\n").replace("\r", "\n")
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


@router.get("/{kb_source_id}/sections", response_model=List[ProjectSectionResponse])
def list_subscribed_project_sections(
    kb_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Curriculum sections for a kb source the user is subscribed to."""
    source = db.query(KBSource).filter(KBSource.id == kb_source_id).first()
    if not source:
        raise HTTPException(
            status_code=404,
            detail={"code": "source_not_found", "message": "Project source not found"},
        )
    subscribed = (
        db.query(UserKbSourceSubscription)
        .filter(
            UserKbSourceSubscription.user_id == current_user.id,
            UserKbSourceSubscription.kb_source_id == kb_source_id,
        )
        .first()
    )
    if not subscribed:
        raise HTTPException(
            status_code=403,
            detail={"code": "not_subscribed", "message": "Subscribe to this project to view its sections."},
        )
    rows = (
        db.query(Section)
        .filter(Section.kb_source_id == kb_source_id)
        .order_by(Section.section_order.asc(), Section.id.asc())
        .all()
    )
    return [
        ProjectSectionResponse(
            id=s.id,
            section_order=s.section_order,
            section_name=s.section_name or "",
            curriculum_section_key=s.section_id or "",
            description_preview=_preview_text(
                (s.section_description or "").strip()
                or (s.section_content or "").strip()
                or (s.section_name or "")
            ),
        )
        for s in rows
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

    total_units = (
        db.query(Section)
        .filter(Section.kb_source_id == payload.kb_source_id)
        .count()
    )
    if total_units == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "no_units",
                "message": "This project has no sections yet. Subscribe after curriculum is loaded.",
            },
        )

    existing = (
        db.query(UserKbSourceSubscription)
        .filter(
            UserKbSourceSubscription.user_id == current_user.id,
            UserKbSourceSubscription.kb_source_id == payload.kb_source_id,
        )
        .first()
    )
    if existing:
        return SubscribeProjectResponse(
            kb_source_id=payload.kb_source_id,
            total_units=total_units,
            created_count=0,
            existing_count=1,
        )

    db.add(
        UserKbSourceSubscription(
            user_id=current_user.id,
            kb_source_id=payload.kb_source_id,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return SubscribeProjectResponse(
            kb_source_id=payload.kb_source_id,
            total_units=total_units,
            created_count=0,
            existing_count=1,
        )

    return SubscribeProjectResponse(
        kb_source_id=payload.kb_source_id,
        total_units=total_units,
        created_count=1,
        existing_count=0,
    )
