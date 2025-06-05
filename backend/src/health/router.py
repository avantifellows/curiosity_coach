import time
import logging
from fastapi import APIRouter
from src.health.schemas import HealthResponse
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["health"]
)

@router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint to verify the API is running"""
    logger.info(f"Health check called - Environment: {settings.APP_ENV}")
    
    response = {
        'status': 'healthy',
        'environment': settings.APP_ENV,
        'timestamp': time.time()
    }
    
    logger.info(f"Health check response: {response}")
    return response 