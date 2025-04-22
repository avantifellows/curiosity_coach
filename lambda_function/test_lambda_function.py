import json
import unittest
from unittest.mock import patch, MagicMock
import lambda_function

class TestLambdaFunction(unittest.TestCase):
    
    @patch('lambda_function.get_message_from_db')
    @patch('lambda_function.call_llm_api')
    @patch('lambda_function.save_message_to_db')
    def test_lambda_handler(self, mock_save_message, mock_call_llm, mock_get_message):
        # Mock return values
        mock_get_message.return_value = {
            "content": "What is a unit test?",
            "additional_params": {}
        }
        
        mock_call_llm.return_value = {
            "response": "A unit test is a way of testing a unit of code.",
            "purpose": "doubt_solver"
        }
        
        mock_save_message.return_value = True
        
        # Test event with single SQS record
        test_event = {
            "Records": [
                {
                    "body": json.dumps({
                        "user_id": "test_user_123",
                        "message_id": "test_message_456",
                        "purpose": "doubt_solver",
                        "conversation_id": "test_conversation_789"
                    })
                }
            ]
        }
        
        # Call the lambda handler
        response = lambda_function.lambda_handler(test_event, {})
        
        # Assertions
        self.assertEqual(response["statusCode"], 200)
        
        # Verify the function called our mocks with the right parameters
        mock_get_message.assert_called_once_with("test_message_456")
        mock_call_llm.assert_called_once()
        mock_save_message.assert_called_once_with(
            user_id="test_user_123",
            content="A unit test is a way of testing a unit of code.",
            is_user=False,
            purpose="doubt_solver"
        )
        
        # Verify the response structure
        body = json.loads(response["body"])
        self.assertEqual(len(body["processed_messages"]), 1)
        self.assertEqual(body["processed_messages"][0]["message_id"], "test_message_456")
        self.assertEqual(body["processed_messages"][0]["purpose"], "doubt_solver")

    @patch('lambda_function.get_message_from_db')
    @patch('lambda_function.call_llm_api')
    @patch('lambda_function.save_message_to_db')
    def test_lambda_handler_default_purpose(self, mock_save_message, mock_call_llm, mock_get_message):
        # Test with missing purpose to ensure default is used
        mock_get_message.return_value = {
            "content": "Hello there",
            "additional_params": {}
        }
        
        mock_call_llm.return_value = {
            "response": "Hi, how can I help you?",
            "purpose": "chat"
        }
        
        test_event = {
            "Records": [
                {
                    "body": json.dumps({
                        "user_id": "test_user_123",
                        "message_id": "test_message_456",
                        "conversation_id": "test_conversation_789"
                        # purpose is missing, should default to "chat"
                    })
                }
            ]
        }
        
        response = lambda_function.lambda_handler(test_event, {})
        
        # Verify default purpose was used
        mock_call_llm.assert_called_once()
        call_args = mock_call_llm.call_args
        self.assertEqual(call_args[0][1], "chat")  # Second argument should be purpose="chat"

if __name__ == '__main__':
    unittest.main() 