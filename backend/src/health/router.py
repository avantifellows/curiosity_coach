import time
from fastapi import APIRouter
from src.health.schemas import HealthResponse
from src.config.settings import settings

router = APIRouter(
    prefix="/api",
    tags=["health"]
)

@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint to verify the API is running"""
    return {
        'status': 'healthy',
        'environment': settings.APP_ENV,
        'timestamp': time.time()
    } 