import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'curiosity_coach'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

def get_connection():
    """Create and return a database connection."""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def init_db():
    """Initialize the database with the schema."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            with open('schema.sql', 'r') as f:
                cursor.execute(f.read())
        conn.commit()

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
            conn.commit()
            return dict(cursor.fetchone())

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
                SELECT content, is_user, timestamp 
                FROM messages 
                WHERE user_id = %s 
                ORDER BY timestamp DESC 
                LIMIT %s
                """,
                (user_id, limit)
            )
            messages = cursor.fetchall()
            return [dict(msg) for msg in messages][::-1]  # Reverse to get chronological order 