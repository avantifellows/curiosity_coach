from fastapi import Header, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session

# Add imports for database and models
from src.database import get_db
from src import models # Assuming User model is in models.py and get_user function exists


def get_user_id(authorization: Optional[str] = Header(None)):
    """
    Extract and validate user ID from authorization header.
    (Kept for potential other uses, but not recommended for returning User object)
    
    Args:
        authorization (str): The 'Authorization' header value
        
    Returns:
        int: Validated user ID
        
    Raises:
        HTTPException: If authorization is missing or invalid
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Unauthorized: Missing or invalid Bearer token format")
    
    try:
        # More robust splitting
        parts = authorization.split(' ')
        if len(parts) != 2 or parts[0] != 'Bearer':
             raise ValueError("Invalid token format")
        user_id = int(parts[1])
        return user_id
    except (ValueError, IndexError):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token content")

# New dependency to get the full User object
async def get_current_user(
    authorization: Optional[str] = Header(None), # Get header
    db: Session = Depends(get_db) # Get DB session
) -> models.User:
    """
    Validates the token, extracts user ID, and retrieves the user object from the database.
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Unauthorized: Missing or invalid Bearer token format")
    
    try:
        # More robust splitting
        parts = authorization.split(' ')
        if len(parts) != 2 or parts[0] != 'Bearer':
             raise ValueError("Invalid token format")
        user_id_str = parts[1]
        user_id = int(user_id_str)
    except (ValueError, IndexError):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token content")
    
    # Fetch user from database using the extracted ID
    # Use direct SQLAlchemy query as there's no specific get_user(id) function
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if user is None:
        # If the user ID from the token doesn't exist in the DB
        raise HTTPException(status_code=401, detail="Unauthorized: User not found")
        
    return user 