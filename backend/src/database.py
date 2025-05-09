import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config.settings import settings

# Database URL
DATABASE_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize the database using the schema defined by SQLAlchemy models."""
    try:
        # Import all models here before calling create_all
        # This ensures they are registered with Base's metadata
        from src import models # Adjust if your models are elsewhere
        
        print("Attempting to create database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully (if they didn't exist)!")
        
        # Optional: Check connection after creation attempt
        with engine.connect() as connection:
             print("Successfully connected to the database after init.")
             
    except Exception as e:
        print(f"Database initialization error: {e}")
        print("Please ensure the database server is running and accessible.")
        print(f"Connection string used: postgresql://{settings.DB_USER}:<PASSWORD>@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        raise
