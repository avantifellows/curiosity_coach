from src.main import process_query
import sys
from src.utils.logger import logger

def run_chat_interface():
    """
    Run a simple command-line chat interface for testing the application.
    """
    print("\nWelcome to the Curiosity Explorer Chat Interface!")
    print("Type your questions about science, history, or any topic you're curious about.")
    print("Type 'exit' or 'quit' to end the session.\n")
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['exit', 'quit']:
                print("\nThank you for using Curiosity Explorer! Goodbye!")
                break
            
            # Skip empty inputs
            if not user_input:
                continue
            
            # Process the query and get response
            print("\nProcessing your question...")
            response = process_query(user_input)
            
            # Display the response
            print("\nCuriosity Explorer:")
            print(response)
            
        except KeyboardInterrupt:
            print("\n\nSession ended by user. Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error in chat interface: {e}", exc_info=True)
            print("\nSorry, there was an error processing your question. Please try again.")

if __name__ == "__main__":
    run_chat_interface() 