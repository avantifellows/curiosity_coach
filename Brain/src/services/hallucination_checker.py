import json
import os
from typing import List, Dict, Tuple
from ..services.llm_service import LLMService


class HallucinationChecker:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.config = self._load_config()
        self.enabled = self._is_enabled()
        
    def _load_config(self) -> Dict:
        """Load hallucination checker configuration."""
        config_path = os.path.join(
            os.path.dirname(__file__), 
            "../../config/prompts/hallucination_checker.json"
        )
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Hallucination checker config not found at {config_path}")
            return {
                "hallucination_check_prompt": "Analyze if the response contains hallucinations. Respond 'true' or 'false'.",
                "system_prompt": "You are a hallucination detector.",
                "temperature": 0.1,
                "max_tokens": 10
            }
    
    def _is_enabled(self) -> bool:
        """Check if hallucination checker is enabled."""
        # Can be controlled via environment variable
        enabled = os.getenv("ENABLE_HALLUCINATION_CHECK", "true").lower() == "true"
        print(f"[HallucinationChecker] Enabled status from env: {enabled}")
        return enabled
    
    def _format_context(self, conversation_history: List[Dict]) -> str:
        """Format conversation history for the prompt."""
        if not conversation_history:
            return "No previous context"
        
        formatted = []
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    async def check_for_hallucination(
        self, 
        query: str, 
        response: str, 
        conversation_history: List[Dict] = None
    ) -> Tuple[bool, Dict]:
        """
        Check if the response contains hallucinations.
        
        Returns:
            Tuple[bool, Dict]: (has_hallucination, check_details)
        """
        if not self.enabled:
            print("[HallucinationChecker] Check skipped - checker is disabled")
            return False, {"checked": False, "reason": "Hallucination checker disabled"}
        
        print(f"[HallucinationChecker] Starting hallucination check for query: '{query[:50]}...'")
        
        try:
            # Format the context
            context = self._format_context(conversation_history or [])
            
            # Prepare the prompt
            check_prompt = self.config["hallucination_check_prompt"].format(
                query=query,
                response=response,
                context=context
            )
            
            # Create messages for the LLM
            messages = [
                {"role": "system", "content": self.config["system_prompt"]},
                {"role": "user", "content": check_prompt}
            ]
            
            # Log the full prompt being sent
            print(f"[HallucinationChecker] System prompt: {self.config['system_prompt']}")
            print(f"[HallucinationChecker] Full check prompt being sent to OpenAI:")
            print(f"{'='*80}")
            print(check_prompt)
            print(f"{'='*80}")
            
            # Get LLM response
            print(f"[HallucinationChecker] Sending check to LLM with prompt length: {len(check_prompt)} chars")
            
            llm_response = self.llm_service.get_completion(
                messages=messages,
                call_type="hallucination_check"
            )
            print(f"Message being sent to LLM: '{messages}'")
            print(f"[HallucinationChecker] LLM response: '{llm_response}'")
            
            # Parse response
            result = llm_response.strip().lower()
            has_hallucination = result == "true"
            
            print(f"[HallucinationChecker] Parsed result: has_hallucination={has_hallucination}")
            
            return has_hallucination, {
                "checked": True,
                "has_hallucination": has_hallucination,
                "raw_response": llm_response,
                "query": query,
                "response_checked": response[:100] + "..." if len(response) > 100 else response
            }
            
        except Exception as e:
            print(f"[HallucinationChecker] ERROR during check: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, {
                "checked": False,
                "error": str(e),
                "reason": "Hallucination check failed"
            }