from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    environment: str
    timestamp: float 