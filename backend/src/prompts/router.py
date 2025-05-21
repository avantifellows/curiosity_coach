from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from src.database import get_db
from . import schemas, service

router = APIRouter(
    prefix="/api",
    tags=["Prompts"],
    responses={404: {"description": "Not found"}},
)

@router.get("/promptHealth")
def prompt_health():
    return {"status": "healthy"}


# --- Prompt Endpoints ---
@router.post("/prompts", response_model=schemas.PromptInDB, status_code=status.HTTP_201_CREATED)
def create_prompt(prompt_in: schemas.PromptCreate, db: Session = Depends(get_db)):
    print(f"Received request to create prompt: {prompt_in}")
    try:
        created_prompt = service.prompt_service.create_prompt(db=db, prompt_create=prompt_in)
        print(f"Prompt created with ID: {created_prompt.id}")
        fetched_prompt = service.prompt_service.get_prompt_by_id(db, created_prompt.id)
        print(f"Successfully fetched prompt for return: {fetched_prompt}")
        return fetched_prompt
    except ValueError as e:
        print(f"Error creating prompt: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/prompts", response_model=List[schemas.PromptSimple])
def list_prompts(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = Query(default=100, le=200)
):
    prompts = service.prompt_service.get_prompts(db=db, skip=skip, limit=limit)
    results = []
    for p in prompts:
        active_version_number = p.active_prompt_version.version_number if p.active_prompt_version else None
        active_version_text = p.active_prompt_version.prompt_text if p.active_prompt_version else None
        results.append(schemas.PromptSimple(
            id=p.id, name=p.name, description=p.description, 
            created_at=p.created_at, updated_at=p.updated_at,
            active_version_number=active_version_number,
            active_version_text=active_version_text
        ))
    return results

@router.get("/prompts/{prompt_id_or_name}", response_model=schemas.PromptInDB)
def get_prompt(prompt_id_or_name: str, db: Session = Depends(get_db)):
    db_prompt = None
    if prompt_id_or_name.isdigit():
        db_prompt = service.prompt_service.get_prompt_by_id(db, int(prompt_id_or_name))
    else:
        db_prompt = service.prompt_service.get_prompt_by_name(db, prompt_id_or_name)
    
    if db_prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return db_prompt

@router.put("/prompts/{prompt_id}", response_model=schemas.PromptInDB)
def update_prompt(prompt_id: int, prompt_in: schemas.PromptUpdate, db: Session = Depends(get_db)):
    try:
        updated_prompt = service.prompt_service.update_prompt(db=db, prompt_id=prompt_id, prompt_update=prompt_in)
        if updated_prompt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        return service.prompt_service.get_prompt_by_id(db, updated_prompt.id) # Re-fetch for full relations
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)):
    deleted_prompt = service.prompt_service.delete_prompt(db=db, prompt_id=prompt_id)
    if deleted_prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return

# --- Prompt Version Endpoints ---
@router.post("/prompts/{prompt_id_or_name}/versions", response_model=schemas.PromptVersionInDB, status_code=status.HTTP_201_CREATED)
def add_prompt_version(
    prompt_id_or_name: str, 
    version_in: schemas.PromptVersionCreate, 
    set_active: Optional[bool] = Query(False, description="Set this new version as active for the prompt."),
    db: Session = Depends(get_db)
):
    db_prompt = None
    if prompt_id_or_name.isdigit():
        db_prompt = service.prompt_service.get_prompt_by_id(db, int(prompt_id_or_name))
    else:
        db_prompt = service.prompt_service.get_prompt_by_name(db, prompt_id_or_name)

    if not db_prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prompt '{prompt_id_or_name}' not found")
    
    try:
        created_version = service.prompt_service.add_prompt_version(
            db=db, 
            prompt_id=db_prompt.id, 
            version_create=version_in,
            set_active=set_active
        )
        return created_version
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/prompts/{prompt_id_or_name}/versions/set-active", response_model=schemas.PromptInDB)
def set_active_version(
    prompt_id_or_name: str,
    request_body: schemas.SetActivePromptVersionRequest,
    db: Session = Depends(get_db)
):
    db_prompt = None
    if prompt_id_or_name.isdigit():
        db_prompt = service.prompt_service.get_prompt_by_id(db, int(prompt_id_or_name))
    else:
        db_prompt = service.prompt_service.get_prompt_by_name(db, prompt_id_or_name)

    if not db_prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prompt '{prompt_id_or_name}' not found")

    try:
        updated_prompt = service.prompt_service.set_active_prompt_version(
            db=db,
            prompt_id=db_prompt.id,
            version_id_to_set_active=request_body.version_id
        )
        if updated_prompt is None: # Should not happen if previous checks pass
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt or version not found during activation")
        return service.prompt_service.get_prompt_by_id(db, updated_prompt.id) # Re-fetch for full relations
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/prompts/{prompt_id_or_name}/versions/active", response_model=schemas.PromptVersionInDB)
def get_active_prompt_version(prompt_id_or_name: str, db: Session = Depends(get_db)):
    active_version = None
    if prompt_id_or_name.isdigit():
        prompt = service.prompt_service.get_prompt_by_id(db, int(prompt_id_or_name))
        if prompt:
            active_version = prompt.active_prompt_version
    else:
        active_version = service.prompt_service.get_active_version_for_prompt(db, prompt_name=prompt_id_or_name)
    
    if active_version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Active prompt version for '{prompt_id_or_name}' not found")
    return active_version

@router.get("/prompts/{prompt_id_or_name}/versions", response_model=List[schemas.PromptVersionInDB])
def list_prompt_versions(prompt_id_or_name: str, db: Session = Depends(get_db)):
    db_prompt = None
    if prompt_id_or_name.isdigit():
        db_prompt = service.prompt_service.get_prompt_by_id(db, int(prompt_id_or_name))
    else:
        db_prompt = service.prompt_service.get_prompt_by_name(db, prompt_id_or_name)
    
    if db_prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prompt '{prompt_id_or_name}' not found")
    return db_prompt.versions 