import time
import logging
import sys
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
    # Use print for immediate CloudWatch output
    print(f"=== HEALTH CHECK CALLED - Environment: {settings.APP_ENV} ===")
    print(f"=== Logger level: {logger.level}, Root logger level: {logging.getLogger().level} ===")
    sys.stdout.flush()  # Force immediate output
    
    # Also use logging
    logger.info(f"Health check called - Environment: {settings.APP_ENV}")
    
    # Force logging to flush immediately
    for handler in logging.getLogger().handlers:
        handler.flush()
    
    response = {
        'status': 'healthy',
        'environment': settings.APP_ENV,
        'timestamp': time.time()
    }
    
    print(f"=== HEALTH CHECK RESPONSE: {response} ===")
    sys.stdout.flush()
    logger.info(f"Health check response: {response}")
    
    # Force logging to flush again
    for handler in logging.getLogger().handlers:
        handler.flush()
    
    return response 