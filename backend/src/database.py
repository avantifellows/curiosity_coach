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

# Remove the old functions that used psycopg2 directly
# get_connection, get_or_create_user, save_message, get_message_count, get_chat_history
# are removed as they are either replaced by SQLAlchemy session management
# or moved/refactored into models.py/crud layer.



# -- Old psycopg2 code removed --

# import os
# import psycopg2
# from psycopg2.extras import RealDictCursor
# from datetime import datetime
# from src.config.settings import settings

# # Database connection parameters
# DB_CONFIG = {
#     'host': settings.DB_HOST,
#     'port': settings.DB_PORT,
#     'database': settings.DB_NAME,
#     'user': settings.DB_USER,
#     'password': settings.DB_PASSWORD
# }

# def get_connection():
#     """Create and return a database connection."""
#     try:
#         return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
#     except Exception as e:
#         print(f"Database connection error: {e}")
#         raise

# def init_db():
#     """Initialize the database with the schema."""
#     try:
#         with get_connection() as conn:
#             with conn.cursor() as cursor:
#                 # Check if schema.sql exists
#                 schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schema.sql')
#                 if os.path.exists(schema_path):
#                     with open(schema_path, 'r') as f:
#                         cursor.execute(f.read())
#                 else:
#                     print("Warning: schema.sql not found. Database schema may not be initialized correctly.")
#             conn.commit()
#             print("Database schema initialized successfully!")
#     except Exception as e:
#         print(f"Database initialization error: {e}")
#         raise 

# def get_or_create_user(phone_number):
#     """Get a user by phone number or create if not exists."""
#     with get_connection() as conn:
#         with conn.cursor() as cursor:
#             # Try to find the user
#             cursor.execute(
#                 "SELECT * FROM users WHERE phone_number = %s",
#                 (phone_number,)
#             )
#             user = cursor.fetchone()
            
#             # If user doesn't exist, create a new one
#             if not user:
#                 cursor.execute(
#                     "INSERT INTO users (phone_number) VALUES (%s) RETURNING *",
#                     (phone_number,)
#                 )
#                 user = cursor.fetchone()
#                 conn.commit()
                
#             return dict(user)

# def save_message(user_id, content, is_user=True):
#     """Save a message to the database."""
#     with get_connection() as conn:
#         with conn.cursor() as cursor:
#             cursor.execute(
#                 "INSERT INTO messages (user_id, content, is_user) VALUES (%s, %s, %s) RETURNING *",
#                 (user_id, content, is_user)
#             )
#             message = cursor.fetchone()
#             conn.commit()
#             return dict(message)

# def get_message_count(user_id):
#     """Get the count of messages sent by a user."""
#     with get_connection() as conn:
#         with conn.cursor() as cursor:
#             cursor.execute(
#                 "SELECT COUNT(*) as count FROM messages WHERE user_id = %s AND is_user = true",
#                 (user_id,)
#             )
#             result = cursor.fetchone()
#             return result['count']

# def get_chat_history(user_id, limit=50):
#     """Get chat history for a user."""
#     with get_connection() as conn:
#         with conn.cursor() as cursor:
#             cursor.execute(
#                 """
#                 SELECT id, content, is_user, timestamp 
#                 FROM messages 
#                 WHERE user_id = %s 
#                 ORDER BY timestamp DESC 
#                 LIMIT %s
#                 """,
#                 (user_id, limit)
#             )
#             messages = cursor.fetchall()
#             # Reverse the order to maintain chronological display (oldest first)
#             return [dict(msg) for msg in reversed(messages)] 
