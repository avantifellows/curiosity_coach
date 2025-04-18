from database import get_message_count

class DummyLLM:
    """A dummy LLM model that will be replaced with a real LLM later."""
    
    def __init__(self):
        pass
    
    def generate_response(self, user_id, user_message):
        """
        Generate a response to the user's message.
        Currently just returns the count of messages the user has sent.
        """
        message_count = get_message_count(user_id)
        
        # Include the new message in the count
        total_messages = message_count + 1
        
        return f"You have sent {total_messages} message{'s' if total_messages != 1 else ''}. This is a placeholder response that will be replaced with a real LLM response later."

# Singleton instance
llm = DummyLLM() 