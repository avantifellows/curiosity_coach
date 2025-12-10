import os
import time
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from src.health.schemas import HealthResponse
from src.config.settings import settings
from src.database import get_db
from src.models import Prompt, PromptVersion
import httpx

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

@router.get("/health/onboarding")
async def check_onboarding_health(db: Session = Depends(get_db)):
    """
    Health check for onboarding system.
    Validates that all onboarding prompts are configured and Brain is accessible.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check 1: Visit prompts configured
    required_purposes = ["visit_1", "visit_2", "visit_3", "steady_state"]
    for purpose in required_purposes:
        prompt = db.query(Prompt).filter(Prompt.prompt_purpose == purpose).first()
        if prompt:
            production_version = db.query(PromptVersion).filter(
                PromptVersion.prompt_id == prompt.id,
                PromptVersion.is_production == True
            ).first()
            health_status["checks"][f"prompt_{purpose}"] = {
                "configured": True,
                "has_production_version": production_version is not None,
                "prompt_id": prompt.id,
                "prompt_name": prompt.name
            }
        else:
            health_status["checks"][f"prompt_{purpose}"] = {
                "configured": False,
                "has_production_version": False
            }
            health_status["status"] = "degraded"
    
    # Check 2: Brain connectivity
    try:
        # Use LOCAL_BRAIN_ENDPOINT_URL only if explicitly set (not default), otherwise use BRAIN_ENDPOINT_URL
        local_brain = os.getenv('LOCAL_BRAIN_ENDPOINT_URL')
        brain_endpoint = local_brain if local_brain else settings.BRAIN_ENDPOINT_URL
        if brain_endpoint:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{brain_endpoint}/health", timeout=30.0)
            health_status["checks"]["brain_connectivity"] = {
                "reachable": response.status_code == 200,
                "endpoint": brain_endpoint,
                "status_code": response.status_code
            }
        else:
            health_status["checks"]["brain_connectivity"] = {
                "reachable": False,
                "error": "Brain endpoint not configured"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["brain_connectivity"] = {
            "reachable": False,
            "endpoint": brain_endpoint,
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check 3: Database connectivity
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {"connected": True}
    except Exception as e:
        health_status["checks"]["database"] = {"connected": False, "error": str(e)}
        health_status["status"] = "unhealthy"
    
    # Return appropriate status code
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code) 