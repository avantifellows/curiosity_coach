from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import time
from database import init_db, get_or_create_user, save_message, get_chat_history, get_message_count
from queue_service import queue_service
from dotenv import load_dotenv

# Load the appropriate environment file
env_file = '.env.local' # if os.getenv('FLASK_ENV') == 'development' else '.env'
load_dotenv(env_file)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize the database
try:
    init_db()
    print("Database initialized successfully!")
except Exception as e:
    print(f"Error initializing database: {e}")
    print("Please ensure PostgreSQL is running and the database credentials are correct.")

def validate_phone_number(phone):
    """Validate phone number format."""
    pattern = re.compile(r'^\d{10,15}$')
    return bool(pattern.match(phone))

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify the API is running"""
    return jsonify({
        'status': 'healthy',
        'environment': os.getenv('FLASK_ENV', 'production'),
        'timestamp': time.time()
    })

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    phone_number = data.get('phone_number')
    print(f"Received phone number: {phone_number}")

    if not phone_number or not validate_phone_number(phone_number):
        return jsonify({
            'success': False,
            'message': 'Invalid phone number. Please enter a 10-15 digit number.'
        }), 400
    
    try:
        # Get or create user
        user = get_or_create_user(phone_number)
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': user
        })
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({
            'success': False,
            'message': f'Error during login: {str(e)}'
        }), 500

@app.route('/api/messages', methods=['POST'])
def send_message():
    # Check for Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'message': 'Unauthorized'}), 401
    
    # Extract user ID from the Authorization header
    try:
        user_id = int(auth_header.split(' ')[1])
    except:
        return jsonify({'message': 'Invalid authorization token'}), 401
    
    data = request.json
    content = data.get('content')
    
    if not content or not content.strip():
        return jsonify({'message': 'Message content cannot be empty'}), 400
    
    try:
        # Save user message to database
        saved_message = save_message(user_id, content, is_user=True)
        
        # Send message to SQS queue for Lambda processing
        queue_service.send_message(
            user_id=user_id,
            message_content=content,
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
        
        return jsonify({
            'success': True,
            'message': saved_message,
            'response': response_message
        })
    except Exception as e:
        print(f"Error sending message: {e}")
        return jsonify({
            'success': False,
            'message': f'Error sending message: {str(e)}'
        }), 500

@app.route('/api/messages/history', methods=['GET'])
def get_messages():
    # Check for Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'message': 'Unauthorized'}), 401
    
    # Extract user ID from the Authorization header
    try:
        user_id = int(auth_header.split(' ')[1])
    except:
        return jsonify({'message': 'Invalid authorization token'}), 401
    
    try:
        # Get chat history
        messages = get_chat_history(user_id)
        return jsonify({
            'success': True,
            'messages': messages
        })
    except Exception as e:
        print(f"Error getting messages: {e}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving messages: {str(e)}'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask server on port {port}...")
    print(f"Environment: {os.getenv('FLASK_ENV', 'production')}")
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') == 'development') 