import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from src.config.settings import settings

# Database connection parameters
DB_CONFIG = {
    'host': settings.DB_HOST,
    'port': settings.DB_PORT,
    'database': settings.DB_NAME,
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD
}

def get_connection():
    """Create and return a database connection."""
    try:
        return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def init_db():
    """Initialize the database with the schema."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # Check if schema.sql exists
                schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schema.sql')
                if os.path.exists(schema_path):
                    with open(schema_path, 'r') as f:
                        cursor.execute(f.read())
                else:
                    print("Warning: schema.sql not found. Database schema may not be initialized correctly.")
            conn.commit()
            print("Database schema initialized successfully!")
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise 