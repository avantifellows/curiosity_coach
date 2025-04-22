from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import os
import re
import time
from typing import Optional, List, Dict, Any, Union
from src.database import init_db, get_or_create_user, save_message, get_chat_history, get_message_count
from queue_service import queue_service
from dotenv import load_dotenv

# Load the appropriate environment file
env_file = '.env.local' # if os.getenv('APP_ENV') == 'development' else '.env'
load_dotenv(env_file)

app = FastAPI(
    title="Curiosity Coach API",
    description="Backend API for Curiosity Coach application",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the database
try:
    init_db()
    print("Database initialized successfully!")
except Exception as e:
    print(f"Error initializing database: {e}")
    print("Please ensure PostgreSQL is running and the database credentials are correct.")

# Pydantic models for request/response validation
class PhoneNumberRequest(BaseModel):
    phone_number: str
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if not re.match(r'^\d{10,15}$', v):
            raise ValueError('Invalid phone number. Please enter a 10-15 digit number.')
        return v

class MessageRequest(BaseModel):
    content: str
    
    @validator('content')
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v

class HealthResponse(BaseModel):
    status: str
    environment: str
    timestamp: float

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    success: bool
    message: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None

class ChatHistoryResponse(BaseModel):
    success: bool
    messages: List[Dict[str, Any]]

def get_user_id(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        user_id = int(authorization.split(' ')[1])
        return user_id
    except:
        raise HTTPException(status_code=401, detail="Invalid authorization token")

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint to verify the API is running"""
    return {
        'status': 'healthy',
        'environment': os.getenv('APP_ENV', 'production'),
        'timestamp': time.time()
    }

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: PhoneNumberRequest):
    phone_number = request.phone_number
    print(f"Received phone number: {phone_number}")
    
    try:
        # Get or create user
        user = get_or_create_user(phone_number)
        
        return {
            'success': True,
            'message': 'Login successful',
            'user': user
        }
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=f"Error during login: {str(e)}")

@app.post("/api/messages", response_model=MessageResponse)
async def send_message(request: MessageRequest, user_id: int = Depends(get_user_id)):
    content = request.content
    
    try:
        # Save user message to database
        saved_message = save_message(user_id, content, is_user=True)
        
        # Send message to SQS queue for Lambda processing
        queue_service.send_message(
            user_id=user_id,
            message_content=content,
            purpose="chat",
            message_id=saved_message['id']
        )
        
        # Simulate a response from Lambda
        # In a real app, this would be handled asynchronously
        time.sleep(0.5)  # Simulate processing time
        
        # Get message count
        message_count = get_message_count(user_id)
        
        # Generate a response (simulating Lambda)
        response_text = f"You have sent {message_count} message{'s' if message_count != 1 else ''}. This is a placeholder response from the backend."
        
        # Save the response
        response_message = save_message(user_id, response_text, is_user=False)
        
        return {
            'success': True,
            'message': saved_message,
            'response': response_message
        }
    except Exception as e:
        print(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

@app.get("/api/messages/history", response_model=ChatHistoryResponse)
async def get_messages(user_id: int = Depends(get_user_id)):
    try:
        # Get chat history
        messages = get_chat_history(user_id)
        return {
            'success': True,
            'messages': messages
        }
    except Exception as e:
        print(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving messages: {str(e)}")

# For local development
if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting FastAPI server on port {port}...")
    print(f"Environment: {os.getenv('APP_ENV', 'production')}")
    print(f"API Documentation: http://localhost:{port}/api/docs")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=os.getenv('APP_ENV') == 'development') 