import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load the appropriate environment file
env_file = '.env.staging' # if local or prod or staging
load_dotenv(env_file)

class Settings(BaseSettings):
    """Application settings."""
    # App settings
    APP_ENV: str = os.getenv('APP_ENV', 'production')
    PORT: int = int(os.getenv('PORT', 5000))
    
    # Database settings
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: str = os.getenv('DB_PORT', '5432')
    DB_NAME: str = os.getenv('DB_NAME', 'curiosity_coach')
    DB_USER: str = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'postgres')
    
    # Local Brain Endpoint (for development)
    LOCAL_BRAIN_ENDPOINT_URL: str = os.getenv('LOCAL_BRAIN_ENDPOINT_URL', 'http://127.0.0.1:5001')
    
    # AWS settings
    AWS_ACCESS_KEY_ID: str = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY: str = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_REGION: str = os.getenv('AWS_REGION', 'ap-south-1')
    SQS_QUEUE_URL: str = os.getenv('SQS_QUEUE_URL', '')
    
    # API settings
    API_TITLE: str = "Curiosity Coach API"
    API_DESCRIPTION: str = "Backend API for Curiosity Coach application"
    API_VERSION: str = "1.0.0"
    API_DOCS_URL: str = "/api/docs"
    API_REDOC_URL: str = "/api/redoc"
    API_OPENAPI_URL: str = "/api/openapi.json"
    
    # Memory Generation
    MEMORY_INACTIVITY_THRESHOLD_HOURS: int = int(os.getenv('MEMORY_INACTIVITY_THRESHOLD_HOURS', 24))
    
    class Config:
        env_file = env_file

settings = Settings() 