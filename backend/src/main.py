from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import sys
from src.auth.router import router as auth_router
from src.messages.router import router as messages_router
from src.conversations.router import router as conversations_router
from src.health.router import router as health_router
from src.prompts.router import router as prompts_router
from src.config.settings import settings
from src.database import init_db
from mangum import Mangum

# Add immediate debugging
print("=== LAMBDA STARTING - MAIN.PY IMPORT ===")
sys.stdout.flush()

# Configure logging for Lambda
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Force the root logger to INFO level explicitly
logging.getLogger().setLevel(logging.INFO)

print(f"=== LOGGING CONFIGURED - Root Level: {logging.getLogger().level} ===")
print(f"=== LOGGING LEVEL CONSTANTS - INFO: {logging.INFO}, WARNING: {logging.WARNING} ===")
sys.stdout.flush()

# Test logging immediately
test_logger = logging.getLogger("test")
test_logger.info("=== TEST LOG MESSAGE - This should appear if logging works ===")

print(f"=== LOGGING CONFIGURED - Level: {logging.getLogger().level} ===")
sys.stdout.flush()

# Prevent duplicate logs from uvicorn when running locally
if settings.APP_ENV != 'development':
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.error").propagate = False

logger = logging.getLogger(__name__)

print(f"=== LOGGER CREATED - APP_ENV: {settings.APP_ENV} ===")
sys.stdout.flush()

def create_app() -> FastAPI:
    """Create and configure a FastAPI application."""
    print(f"=== CREATE_APP CALLED - Environment: {settings.APP_ENV} ===")
    sys.stdout.flush()
    
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
        print("=== FASTAPI STARTUP EVENT TRIGGERED ===")
        sys.stdout.flush()
        logger.info("FastAPI application starting up...")
        try:
            # Add any initialization tasks here
            logger.info("Application startup completed successfully")
            print("=== FASTAPI STARTUP COMPLETED ===")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error during startup: {str(e)}")
            print(f"=== STARTUP ERROR: {str(e)} ===")
            sys.stdout.flush()
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
    
    print(f"=== CORS ORIGINS: {allowed_origins} ===")
    sys.stdout.flush()
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
    app.include_router(auth_router)
    app.include_router(messages_router)
    app.include_router(conversations_router)
    app.include_router(health_router)
    app.include_router(prompts_router)
    
    print("=== FASTAPI APP CREATED SUCCESSFULLY ===")
    sys.stdout.flush()
    logger.info("FastAPI app created successfully")
    return app

print("=== CALLING CREATE_APP ===")
sys.stdout.flush()
_fastapi_app = create_app()

# Conditionally wrap with Mangum for serverless deployment
if settings.APP_ENV != 'development':
    print("=== WRAPPING WITH MANGUM FOR LAMBDA ===")
    sys.stdout.flush()
    logger.info("Wrapping FastAPI app with Mangum for Lambda")
    app = Mangum(_fastapi_app)
    print("=== MANGUM WRAPPER CREATED ===")
    sys.stdout.flush()
else:
    app = _fastapi_app # Use the raw FastAPI app for local dev

print("=== MAIN.PY INITIALIZATION COMPLETE ===")
sys.stdout.flush()

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