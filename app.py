import gradio as gr
import re
from database import init_db, get_or_create_user, save_message, get_chat_history
from model import llm

# Initialize the database
init_db()

# Global variable to store the current user ID
current_user_id = None

def validate_phone_number(phone):
    """Validate phone number format."""
    # Simple validation to check if the phone number contains only digits
    pattern = re.compile(r'^\d{10,15}$')
    return bool(pattern.match(phone))

def login(phone_number):
    """Login with phone number and return success/failure message."""
    global current_user_id
    
    if not validate_phone_number(phone_number):
        return "Invalid phone number. Please enter a 10-15 digit number.", gr.update(visible=True), gr.update(visible=False)
    
    # Get or create user
    user = get_or_create_user(phone_number)
    current_user_id = user['id']
    
    # Get chat history
    chat_history = get_chat_history(current_user_id)
    formatted_history = []
    
    for msg in chat_history:
        if msg['is_user']:
            formatted_history.append([msg['content'], None])
        else:
            if len(formatted_history) > 0 and formatted_history[-1][1] is None:
                formatted_history[-1][1] = msg['content']
            else:
                formatted_history.append([None, msg['content']])
    
    return f"Logged in successfully with phone number: {phone_number}", gr.update(visible=False), gr.update(visible=True, value=formatted_history)

def chat(message, history):
    """Process user message and generate a response."""
    global current_user_id
    
    if current_user_id is None:
        return "Please login first."
    
    # Save user message
    save_message(current_user_id, message, is_user=True)
    
    # Get response from LLM
    response = llm.generate_response(current_user_id, message)
    
    # Save model response
    save_message(current_user_id, response, is_user=False)
    
    # Return the response to update the chat interface
    return response

# Create Gradio blocks
with gr.Blocks(title="Curiosity Coach Chat") as demo:
    gr.Markdown("# Welcome to Curiosity Coach")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## Login")
            with gr.Group() as login_group:
                phone_input = gr.Textbox(label="Phone Number (10-15 digits)")
                login_button = gr.Button("Login")
                login_message = gr.Textbox(label="Login Status", interactive=False)
            
        with gr.Column(scale=3):
            chat_interface = gr.ChatInterface(
                chat,
                chatbot=gr.Chatbot(height=600, visible=False),
                title="Chat with Curiosity Coach",
                theme="soft",
                examples=["How can you help me?", "Tell me about yourself", "What's the weather like today?"],
                retry_btn=None,
                undo_btn=None,
                clear_btn="Clear",
            )
    
    # Handle login button click
    login_button.click(
        fn=login,
        inputs=[phone_input],
        outputs=[login_message, login_group, chat_interface.chatbot]
    )

if __name__ == "__main__":
    demo.launch() 