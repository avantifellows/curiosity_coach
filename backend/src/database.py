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

def get_or_create_user(phone_number):
    """Get a user by phone number or create if not exists."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Try to find the user
            cursor.execute(
                "SELECT * FROM users WHERE phone_number = %s",
                (phone_number,)
            )
            user = cursor.fetchone()
            
            # If user doesn't exist, create a new one
            if not user:
                cursor.execute(
                    "INSERT INTO users (phone_number) VALUES (%s) RETURNING *",
                    (phone_number,)
                )
                user = cursor.fetchone()
                conn.commit()
                
            return dict(user)

def save_message(user_id, content, is_user=True):
    """Save a message to the database."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO messages (user_id, content, is_user) VALUES (%s, %s, %s) RETURNING *",
                (user_id, content, is_user)
            )
            message = cursor.fetchone()
            conn.commit()
            return dict(message)

def get_message_count(user_id):
    """Get the count of messages sent by a user."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as count FROM messages WHERE user_id = %s AND is_user = true",
                (user_id,)
            )
            result = cursor.fetchone()
            return result['count']

def get_chat_history(user_id, limit=50):
    """Get chat history for a user."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, content, is_user, timestamp 
                FROM messages 
                WHERE user_id = %s 
                ORDER BY timestamp DESC 
                LIMIT %s
                """,
                (user_id, limit)
            )
            messages = cursor.fetchall()
            # Reverse the order to maintain chronological display (oldest first)
            return [dict(msg) for msg in reversed(messages)] 