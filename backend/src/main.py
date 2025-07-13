from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from src.auth import router as auth_router
from src.messages import router as messages_router
from src.conversations import router as conversations_router
from src.health import router as health_router
from src.memories import router as memories_router
from src.prompts import router as prompts_router
from src.tasks import router as tasks_router
from src.user_personas import router as user_personas_router
from src.internal import router as internal_router
from src.feedback import router as feedback_router
from src.config.settings import settings
from src.database import init_db
from mangum import Mangum

# Configure logging for Lambda
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Force the root logger to INFO level explicitly
logging.getLogger().setLevel(logging.INFO)

# Prevent duplicate logs from uvicorn when running locally
if settings.APP_ENV != 'development':
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.error").propagate = False

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create and configure a FastAPI application."""
    logger.info(f"Creating FastAPI app - Environment: {settings.APP_ENV}")
    
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url=settings.API_DOCS_URL,
        redoc_url=settings.API_REDOC_URL,
        openapi_url=settings.API_OPENAPI_URL
    )
    
    @app.on_event("startup")
    async def startup_event():
        """Run initialization tasks on application startup"""
        logger.info("FastAPI application starting up...")
        try:
            # Add any initialization tasks here
            logger.info("Application startup completed successfully")
        except Exception as e:
            logger.error(f"Error during startup: {str(e)}")
            raise
    
    # Get CORS origins from environment
    frontend_url = os.getenv("FRONTEND_URL", "")
    s3_website_url = os.getenv("S3_WEBSITE_URL", "")
    
    # Build allowed origins list
    allowed_origins = [
        "http://localhost:8001",
        "http://localhost:3000", # Common port for local React dev
        "http://localhost:5173", # Common port for local Vite dev
    ]
    
    # Add production URLs if they exist
    if frontend_url:
        allowed_origins.append(frontend_url)
        # Also add without trailing slash if it exists
        if frontend_url.endswith("/"):
            allowed_origins.append(frontend_url.rstrip("/"))
    
    if s3_website_url:
        allowed_origins.append(s3_website_url)
        # Also add without trailing slash if it exists
        if s3_website_url.endswith("/"):
            allowed_origins.append(s3_website_url.rstrip("/"))
    
    # For development/testing, allow all origins if specified
    if os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true":
        allowed_origins = ["*"]
    
    logger.info(f"CORS allowed origins: {allowed_origins}")
    
    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"], # Or specify methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        allow_headers=["*"], # Or specify headers: ["Content-Type", "Authorization"]
    )
    
    # Include routers
    app.include_router(auth_router.router)
    app.include_router(conversations_router.router)
    app.include_router(health_router.router)
    app.include_router(memories_router.router)
    app.include_router(messages_router.router)
    app.include_router(prompts_router.router)
    app.include_router(tasks_router.router)
    app.include_router(user_personas_router.router)
    app.include_router(internal_router.router)
    app.include_router(feedback_router.router)
    
    logger.info("FastAPI app created successfully")
    return app

_fastapi_app = create_app()

# Conditionally wrap with Mangum for serverless deployment
if settings.APP_ENV != 'development':
    logger.info("Wrapping FastAPI app with Mangum for Lambda")
    app = Mangum(_fastapi_app)
else:
    app = _fastapi_app # Use the raw FastAPI app for local dev

# For local development
if __name__ == '__main__':
    import uvicorn
    
    port = settings.PORT
    print(f"Starting FastAPI server on port {port}...")
    print(f"Environment: {settings.APP_ENV}")
    print(f"API Documentation: http://localhost:{port}{settings.API_DOCS_URL}")
    
    # Point uvicorn directly to the created app instance for local run
    uvicorn.run(app, 
                host="0.0.0.0", 
                port=port,
                log_level="info",
                access_log=False,  # Disable access logs from Uvicorn
                reload=settings.APP_ENV == 'development') 