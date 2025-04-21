from src.database import get_connection

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
                SELECT content, is_user, timestamp 
                FROM messages 
                WHERE user_id = %s 
                ORDER BY timestamp ASC 
                LIMIT %s
                """,
                (user_id, limit)
            )
            messages = cursor.fetchall()
            return [dict(msg) for msg in messages] 