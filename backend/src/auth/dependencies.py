from fastapi import Header, HTTPException
from typing import Optional

def get_user_id(authorization: Optional[str] = Header(None)):
    """
    Extract and validate user ID from authorization header.
    
    Args:
        authorization (str): The 'Authorization' header value
        
    Returns:
        int: Validated user ID
        
    Raises:
        HTTPException: If authorization is missing or invalid
    """
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        user_id = int(authorization.split(' ')[1])
        return user_id
    except:
        raise HTTPException(status_code=401, detail="Invalid authorization token") 