from sqlalchemy.orm import Session
from src import models
from src.user_personas import schemas

def create_or_update_user_persona(db: Session, persona: schemas.UserPersonaCreate) -> models.UserPersona:
    """
    Creates a new user persona or updates an existing one.
    """
    db_persona = db.query(models.UserPersona).filter(models.UserPersona.user_id == persona.user_id).first()

    if db_persona:
        # Update existing persona
        db_persona.persona_data = persona.persona_data
        db.add(db_persona)
    else:
        # Create new persona
        db_persona = models.UserPersona(
            user_id=persona.user_id,
            persona_data=persona.persona_data
        )
        db.add(db_persona)
    
    db.commit()
    db.refresh(db_persona)
    return db_persona 