from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from src.auth.router import router as auth_router
from src.messages.router import router as messages_router
from src.conversations.router import router as conversations_router
from src.health.router import router as health_router
from src.config.settings import settings
from src.database import init_db
from mangum import Mangum

# Configure logging to prevent duplicate logs
logging.getLogger("uvicorn.access").propagate = False
logging.getLogger("uvicorn.error").propagate = False

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def create_app() -> FastAPI:
    """Create and configure a FastAPI application."""
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url=settings.API_DOCS_URL,
        redoc_url=settings.API_REDOC_URL,
        openapi_url=settings.API_OPENAPI_URL
    )
    
    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        # Use allow_origins for exact matches like localhost and deployed frontend
        allow_origins=[
            "http://localhost:6000",
            "http://localhost:3000", # Common port for local React dev
            "http://localhost:5173", # Common port for local Vite dev
            "http://curiosity-coach-frontend-dev.s3-website.ap-south-1.amazonaws.com", # Explicitly add S3 origin
        ],
        allow_credentials=True,
        allow_methods=["*"], # Or specify methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        allow_headers=["*"], # Or specify headers: ["Content-Type", "Authorization"]
    )
    
    # Include routers
    app.include_router(auth_router)
    app.include_router(messages_router)
    app.include_router(conversations_router)
    app.include_router(health_router)

    
    # Initialize the database
    # try:
    #     init_db()
    #     print("Database initialized successfully!")
    # except Exception as e:
    #     print(f"Error initializing database: {e}")
    #     print("Please ensure PostgreSQL is running and the database credentials are correct.")
    
    return app

_fastapi_app = create_app()

# Conditionally wrap with Mangum for serverless deployment
if settings.APP_ENV != 'development':
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