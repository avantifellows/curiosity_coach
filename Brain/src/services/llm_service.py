import json
import os
from typing import Dict, Any, Optional
from openai import OpenAI
from groq import Groq
from dotenv import load_dotenv
from src.utils.logger import logger

# Load environment variables
load_dotenv()

class LLMService:
    """Factory class for LLM services with support for different configurations per call type"""
    
    def __init__(self, config_path: str = "config/llm_config.json"):
        logger.debug(f"Initializing LLMService with config: {config_path}")
        self.config = self._load_config(config_path)
        self.default_provider = self.config["default_provider"]
        logger.info(f"LLMService initialized with default provider: {self.default_provider}")
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load the LLM configuration from JSON file"""
        try:
            # Get the absolute path to the config file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_abs_path = os.path.join(project_root, config_path)
            
            logger.debug(f"Loading config from: {config_abs_path}")
            with open(config_abs_path, 'r') as f:
                config = json.load(f)
            logger.debug("Successfully loaded LLM configuration")
            return config
        except FileNotFoundError:
            logger.error(f"LLM configuration file not found at {config_path}")
            raise FileNotFoundError(f"LLM configuration file not found at {config_path}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in configuration file at {config_path}")
            raise ValueError(f"Invalid JSON in configuration file at {config_path}")
    
    def get_client(self, provider: str) -> Any:
        """Get the appropriate LLM client based on provider"""
        logger.debug(f"Getting client for provider: {provider}")
        api_key_env = self.config["providers"][provider]["api_key_env"]
        api_key = os.getenv(api_key_env)
        
        if not api_key:
            logger.error(f"API key not found for provider {provider} in environment variable {api_key_env}")
            raise ValueError(f"API key not found for provider {provider} in environment variable {api_key_env}")
            
        if provider == "openai":
            logger.debug("Creating OpenAI client")
            return OpenAI(api_key=api_key)
        elif provider == "groq":
            logger.debug("Creating Groq client")
            return Groq(api_key=api_key)
        else:
            logger.error(f"Unsupported LLM provider: {provider}")
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def get_call_config(self, call_type: str) -> Dict[str, Any]:
        """Get the configuration for a specific call type"""
        logger.debug(f"Getting call configuration for type: {call_type}")
        if call_type not in self.config["calls"]:
            logger.error(f"Unknown call type: {call_type}")
            raise ValueError(f"Unknown call type: {call_type}")
        return self.config["calls"][call_type]
    
    def get_completion(self, messages: list, call_type: Optional[str] = None) -> str:
        """
        Get completion from the configured LLM provider
        
        Args:
            messages: List of message dictionaries
            call_type: Optional call type to use specific configuration
        """
        if os.getenv("APP_ENV") == "test":
            logger.info(f"APP_ENV is 'test', returning mocked LLM completion for call_type: {call_type}")

            # Check for memory generation prompt
            if any("You are a meticulous educational analyst" in msg.get("content", "") for msg in messages):
                logger.info("Detected memory generation prompt, returning mocked memory JSON.")
                return json.dumps({
                    "conversation_summary": "This is a mocked summary.",
                    "topics_discussed": [],
                    "student_profile_insights": {},
                    "future_conversation_hooks": []
                })

            if call_type == "intent_gathering":
                return json.dumps({
                    "needs_clarification": False,
                    "query": "mocked query",
                    "subject": {"main_topic": "mocked topic", "related_topics": []},
                    "intents": {"primary_intent": "educational", "secondary_intent": "curiosity"},
                    "context": {"known_information": "none", "motivation": "learning", "learning_goal": "mocked goal"}
                })
            elif call_type == "simplified_conversation":
                return json.dumps({
                    "response": "This is a mocked simplified response.",
                    "needs_clarification": False,
                    "follow_up_questions": []
                })

            return "This is a mocked LLM response."

        try:
            if call_type:
                logger.debug(f"Using specific call type: {call_type}")
                call_config = self.get_call_config(call_type)
                provider = call_config["provider"]
            else:
                logger.debug("Using default provider and call type")
                provider = self.default_provider
                call_config = self.config["calls"]["response_generation"]
            
            logger.info(f"Making LLM call to {provider} with model {call_config['model']}")
            client = self.get_client(provider)
            
            response = client.chat.completions.create(
                model=call_config["model"],
                messages=messages,
                temperature=call_config["temperature"],
                max_tokens=call_config["max_tokens"]
            )
            
            logger.debug("Successfully received completion from LLM")
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error getting completion: {str(e)}", exc_info=True)
            raise

    def generate_response(self, final_prompt: str, call_type: Optional[str] = None) -> Dict[str, str]:
        """
        Generate a response from the final prompt and return it in a dictionary format.
        
        Args:
            final_prompt (str): The final prompt to generate a response from
            call_type (str, optional): The type of call to use specific configuration
            
        Returns:
            Dict[str, str]: A dictionary with 'raw_response' as the key and the generated text as the value
        """
        logger.debug(f"Generating response for prompt with call type: {call_type}")
        messages = [
            {"role": "user", "content": final_prompt}
        ]
        
        try:
            generated_text = self.get_completion(messages, call_type)
            logger.debug("Successfully generated response")
            return {"raw_response": generated_text}
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            raise 