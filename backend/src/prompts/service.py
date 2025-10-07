from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, and_, or_
from typing import List, Optional

from src.models import Prompt, PromptVersion
from . import schemas

class PromptService:
    def get_prompt_by_id(self, db: Session, prompt_id: int) -> Optional[Prompt]:
        return db.query(Prompt).options(selectinload(Prompt.versions), selectinload(Prompt.active_prompt_version)).filter(Prompt.id == prompt_id).first()

    def get_prompt_by_name(self, db: Session, name: str) -> Optional[Prompt]:
        return db.query(Prompt).options(selectinload(Prompt.versions), selectinload(Prompt.active_prompt_version)).filter(Prompt.name == name).first()

    def get_prompts(self, db: Session, skip: int = 0, limit: int = 100) -> List[Prompt]:
        return db.query(Prompt).options(selectinload(Prompt.active_prompt_version)).offset(skip).limit(limit).all()
    
    def get_prompts_by_purpose(self, db: Session, purpose: str) -> List[Prompt]:
        """Get all prompts with a specific purpose."""
        return db.query(Prompt).options(selectinload(Prompt.active_prompt_version)).filter(Prompt.prompt_purpose == purpose).all()

    def create_prompt(self, db: Session, prompt_create: schemas.PromptCreate) -> Prompt:
        existing_prompt = self.get_prompt_by_name(db, name=prompt_create.name)
        if existing_prompt:
            raise ValueError(f"Prompt with name '{prompt_create.name}' already exists.")

        db_prompt = Prompt(
            name=prompt_create.name,
            description=prompt_create.description,
            prompt_purpose=prompt_create.prompt_purpose
        )
        db.add(db_prompt)
        db.commit()
        db.refresh(db_prompt)

        if prompt_create.initial_version_text:
            self.add_prompt_version(
                db,
                prompt_id=db_prompt.id,
                version_create=schemas.PromptVersionCreate(prompt_text=prompt_create.initial_version_text),
                set_active=True # Make the initial version active
            )
            db.refresh(db_prompt) # Refresh to get the active_prompt_version relationship populated

        return db_prompt

    def update_prompt(self, db: Session, prompt_id: int, prompt_update: schemas.PromptUpdate) -> Optional[Prompt]:
        db_prompt = self.get_prompt_by_id(db, prompt_id)
        if not db_prompt:
            return None
        
        if prompt_update.name and prompt_update.name != db_prompt.name:
            existing_prompt = self.get_prompt_by_name(db, name=prompt_update.name)
            if existing_prompt and existing_prompt.id != prompt_id:
                 raise ValueError(f"Another prompt with name '{prompt_update.name}' already exists.")
            db_prompt.name = prompt_update.name
        
        if prompt_update.description is not None:
            db_prompt.description = prompt_update.description
        
        if prompt_update.prompt_purpose is not None:
            db_prompt.prompt_purpose = prompt_update.prompt_purpose
        
        db.commit()
        db.refresh(db_prompt)
        return db_prompt

    def delete_prompt(self, db: Session, prompt_id: int) -> Optional[Prompt]:
        db_prompt = self.get_prompt_by_id(db, prompt_id)
        if not db_prompt:
            return None
        db.delete(db_prompt) # Versions will be cascade deleted due to relationship setting
        db.commit()
        return db_prompt

    def get_prompt_version_by_id(self, db: Session, version_id: int) -> Optional[PromptVersion]:
        return db.query(PromptVersion).filter(PromptVersion.id == version_id).first()

    def get_prompt_version_by_version_number(self, db: Session, prompt_id: int, version_number: int) -> Optional[PromptVersion]:
        return db.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt_id,
            PromptVersion.version_number == version_number
        ).first()

    def add_prompt_version(self, db: Session, prompt_id: int, version_create: schemas.PromptVersionCreate, set_active: bool = False, user_id: Optional[int] = None, set_production: bool = False) -> PromptVersion:
        db_prompt = self.get_prompt_by_id(db, prompt_id)
        if not db_prompt:
            raise ValueError(f"Prompt with id {prompt_id} not found.")

        # Determine the next version number
        last_version = db.query(func.max(PromptVersion.version_number)).filter(PromptVersion.prompt_id == prompt_id).scalar()
        next_version_number = (last_version or 0) + 1

        db_version = PromptVersion(
            prompt_id=prompt_id,
            prompt_text=version_create.prompt_text,
            version_number=next_version_number,
            user_id=user_id,
            is_active=False, # Initially set to false, then handle activation
            is_production=set_production or version_create.is_production or False
        )
        db.add(db_version)
        db.commit() # Commit to get an ID for db_version
        db.refresh(db_version)

        if set_active:
            self.set_active_prompt_version(db, prompt_id=prompt_id, version_id_to_set_active=db_version.id)
        
        return db_version

    def set_active_prompt_version(self, db: Session, prompt_id: int, version_id_to_set_active: int) -> Optional[Prompt]:
        db_prompt = self.get_prompt_by_id(db, prompt_id)
        if not db_prompt:
            raise ValueError(f"Prompt with id {prompt_id} not found.")

        version_to_activate = self.get_prompt_version_by_id(db, version_id_to_set_active)
        if not version_to_activate or version_to_activate.prompt_id != prompt_id:
            raise ValueError(f"PromptVersion with id {version_id_to_set_active} not found or does not belong to prompt {prompt_id}.")

        # Deactivate current active version(s) for this prompt_id
        db.query(PromptVersion)\
            .filter(PromptVersion.prompt_id == prompt_id, PromptVersion.is_active == True)\
            .update({"is_active": False}, synchronize_session=False)

        # Activate the new version
        version_to_activate.is_active = True
        db.add(version_to_activate)
        db.commit()
        db.refresh(db_prompt)
        db.refresh(version_to_activate) # Ensure the version_to_activate object reflects the change
        return db_prompt

    def get_active_version_for_prompt(self, db: Session, prompt_name: str) -> Optional[PromptVersion]:
        prompt = self.get_prompt_by_name(db, name=prompt_name)
        if prompt and prompt.active_prompt_version:
            return prompt.active_prompt_version
        # Fallback if relationship isn't loaded or to be absolutely sure
        return db.query(PromptVersion)\
            .join(Prompt, PromptVersion.prompt_id == Prompt.id)\
            .filter(Prompt.name == prompt_name, PromptVersion.is_active == True)\
            .first()

    # New methods for user-specific versioning
    def get_user_prompt_versions(self, db: Session, prompt_id: int, user_id: int) -> List[PromptVersion]:
        """Get all prompt versions created by a specific user for a specific prompt."""
        return db.query(PromptVersion)\
            .filter(PromptVersion.prompt_id == prompt_id, PromptVersion.user_id == user_id)\
            .order_by(PromptVersion.version_number.desc())\
            .all()

    def get_earliest_prompt_version(self, db: Session, prompt_name: str) -> Optional[PromptVersion]:
        """Get the earliest (lowest version number) prompt version for a prompt."""
        return db.query(PromptVersion)\
            .join(Prompt, PromptVersion.prompt_id == Prompt.id)\
            .filter(Prompt.name == prompt_name)\
            .order_by(PromptVersion.version_number.asc())\
            .first()

    def get_global_prompt_versions(self, db: Session, prompt_id: int) -> List[PromptVersion]:
        """Get all prompt versions that are global (no user_id) for a specific prompt."""
        return db.query(PromptVersion)\
            .filter(PromptVersion.prompt_id == prompt_id, PromptVersion.user_id.is_(None))\
            .order_by(PromptVersion.version_number.desc())\
            .all()

    def get_prompt_versions_for_user(self, db: Session, prompt_id: int, user_id: Optional[int] = None) -> List[PromptVersion]:
        """
        Get prompt versions visible to a user:
        - If user_id is None, return only global versions
        - If user_id is provided, return user's versions + global versions
        """
        if user_id is None:
            # Return only global versions
            return self.get_global_prompt_versions(db, prompt_id)
        else:
            # Return user's versions AND global versions
            return db.query(PromptVersion)\
                .filter(
                    PromptVersion.prompt_id == prompt_id,
                    or_(PromptVersion.user_id == user_id, PromptVersion.user_id.is_(None))
                )\
                .order_by(PromptVersion.version_number.desc())\
                .all()

    # New methods for production versioning
    def get_production_prompt_version(self, db: Session, prompt_name: str) -> Optional[PromptVersion]:
        """Get the production version for a prompt. Falls back to active version if no production version exists."""
        # First try to get a production version
        production_version = db.query(PromptVersion)\
            .join(Prompt, PromptVersion.prompt_id == Prompt.id)\
            .filter(Prompt.name == prompt_name, PromptVersion.is_production == True)\
            .order_by(PromptVersion.version_number.desc())\
            .first()
            
        if production_version:
            return production_version
            
        # Fallback to active version if no production version exists
        return self.get_active_version_for_prompt(db, prompt_name)

    def set_production_prompt_version_by_number(self, db: Session, prompt_id: int, version_number: int) -> Optional[PromptVersion]:
        """Set a specific version as production by version number (only one production version allowed per prompt)."""
        db_prompt = self.get_prompt_by_id(db, prompt_id)
        if not db_prompt:
            raise ValueError(f"Prompt with id {prompt_id} not found.")

        version_to_mark = self.get_prompt_version_by_version_number(db, prompt_id, version_number)
        if not version_to_mark:
            raise ValueError(f"PromptVersion with version number {version_number} not found for prompt {prompt_id}.")

        # First, unset production flag from all other versions of this prompt
        db.query(PromptVersion)\
            .filter(PromptVersion.prompt_id == prompt_id, PromptVersion.is_production == True)\
            .update({"is_production": False}, synchronize_session=False)

        # Then mark the new version as production
        version_to_mark.is_production = True
        db.add(version_to_mark)
        db.commit()
        db.refresh(version_to_mark)
        return version_to_mark

    def set_production_prompt_version(self, db: Session, prompt_id: int, version_id: int) -> Optional[PromptVersion]:
        """Set a specific version as production (only one production version allowed per prompt)."""
        db_prompt = self.get_prompt_by_id(db, prompt_id)
        if not db_prompt:
            raise ValueError(f"Prompt with id {prompt_id} not found.")

        version_to_mark = self.get_prompt_version_by_id(db, version_id)
        if not version_to_mark or version_to_mark.prompt_id != prompt_id:
            raise ValueError(f"PromptVersion with id {version_id} not found or does not belong to prompt {prompt_id}.")

        # First, unset production flag from all other versions of this prompt
        db.query(PromptVersion)\
            .filter(PromptVersion.prompt_id == prompt_id, PromptVersion.is_production == True)\
            .update({"is_production": False}, synchronize_session=False)

        # Then mark the new version as production
        version_to_mark.is_production = True
        db.add(version_to_mark)
        db.commit()
        db.refresh(version_to_mark)
        return version_to_mark

    def unset_production_prompt_version_by_number(self, db: Session, prompt_id: int, version_number: int) -> Optional[PromptVersion]:
        """Remove production flag from a specific version by version number."""
        db_prompt = self.get_prompt_by_id(db, prompt_id)
        if not db_prompt:
            raise ValueError(f"Prompt with id {prompt_id} not found.")

        version_to_unmark = self.get_prompt_version_by_version_number(db, prompt_id, version_number)
        if not version_to_unmark:
            raise ValueError(f"PromptVersion with version number {version_number} not found for prompt {prompt_id}.")

        # Remove production flag
        version_to_unmark.is_production = False
        db.add(version_to_unmark)
        db.commit()
        db.refresh(version_to_unmark)
        return version_to_unmark

    def unset_production_prompt_version(self, db: Session, prompt_id: int, version_id: int) -> Optional[PromptVersion]:
        """Remove production flag from a specific version."""
        db_prompt = self.get_prompt_by_id(db, prompt_id)
        if not db_prompt:
            raise ValueError(f"Prompt with id {prompt_id} not found.")

        version_to_unmark = self.get_prompt_version_by_id(db, version_id)
        if not version_to_unmark or version_to_unmark.prompt_id != prompt_id:
            raise ValueError(f"PromptVersion with id {version_id} not found or does not belong to prompt {prompt_id}.")

        # Remove production flag
        version_to_unmark.is_production = False
        db.add(version_to_unmark)
        db.commit()
        db.refresh(version_to_unmark)
        return version_to_unmark

prompt_service = PromptService() 