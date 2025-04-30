"""
Mock database module for local testing of the Lambda function.
This simulates the database operations used in the actual Lambda function.
"""

import json
import os
from pathlib import Path
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Use a JSON file as a simple mock database
DB_FILE = Path("mock_db.json")

def initialize_db():
    """Initialize the mock database if it doesn't exist"""
    if not DB_FILE.exists():
        with open(DB_FILE, 'w') as f:
            json.dump({
                "messages": {},
                "users": {
                    "test_user_123": {
                        "id": "test_user_123",
                        "name": "Test User"
                    }
                },
                "conversations": {}
            }, f, indent=2)
        logger.info(f"Initialized mock database at {DB_FILE}")
    else:
        logger.info(f"Using existing mock database at {DB_FILE}")

def get_message_from_db(message_id):
    """
    Retrieve a message from the mock database.
    
    Args:
        message_id: The ID of the message to retrieve
        
    Returns:
        dict: Message data or a default value if not found
    """
    initialize_db()
    
    try:
        with open(DB_FILE, 'r') as f:
            db = json.load(f)
        
        # Return the message if it exists, otherwise return a mock message
        if message_id in db["messages"]:
            logger.info(f"Retrieved message {message_id} from mock database")
            return db["messages"][message_id]
        else:
            logger.info(f"Message {message_id} not found, returning mock data")
            return {
                "content": f"This is mock content for message ID: {message_id}",
                "additional_params": {
                    "language": "English",
                    "difficulty": "medium"
                }
            }
    except Exception as e:
        logger.error(f"Error retrieving message from mock DB: {str(e)}")
        # Return default mock data in case of error
        return {
            "content": "Default mock content",
            "additional_params": {}
        }

def save_message_to_db(user_id, content, is_user=False, purpose=None):
    """
    Save a message to the mock database.
    
    Args:
        user_id: The ID of the user
        content: The message content
        is_user: Whether the message is from a user (True) or the system (False)
        purpose: The purpose of the message
        
    Returns:
        bool: True if the message was saved successfully
    """
    initialize_db()
    
    try:
        # Load current database
        with open(DB_FILE, 'r') as f:
            db = json.load(f)
        
        # Create a new message ID
        message_id = f"msg_{len(db['messages']) + 1}"
        
        # Save the message
        db["messages"][message_id] = {
            "id": message_id,
            "user_id": user_id,
            "content": content,
            "is_user": is_user,
            "purpose": purpose,
            "timestamp": str(os.path.getmtime(DB_FILE))
        }
        
        # Write back to the database
        with open(DB_FILE, 'w') as f:
            json.dump(db, f, indent=2)
        
        logger.info(f"Saved message {message_id} to mock database")
        return True
    except Exception as e:
        logger.error(f"Error saving message to mock DB: {str(e)}")
        return False

def list_messages(limit=10):
    """List the most recent messages in the mock database"""
    initialize_db()
    
    try:
        with open(DB_FILE, 'r') as f:
            db = json.load(f)
        
        # Get all messages as a list
        messages = list(db["messages"].values())
        
        # Sort by timestamp (assuming it's stored)
        messages.sort(key=lambda x: x.get("timestamp", "0"), reverse=True)
        
        # Return the most recent messages
        return messages[:limit]
    except Exception as e:
        logger.error(f"Error listing messages from mock DB: {str(e)}")
        return []

def clear_mock_db():
    """Clear the mock database (for testing)"""
    if DB_FILE.exists():
        DB_FILE.unlink()
    initialize_db()
    logger.info("Mock database cleared and reinitialized") 