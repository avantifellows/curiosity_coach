from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from src.main import process_query
from src.utils.logger import logger

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def handle_query():
    try:
        user_input = request.json.get('query', '')
        if not user_input:
            return jsonify({'error': 'No query provided'}), 400
        
        # Process the query and get response
        response = process_query(user_input)
        
        return jsonify({
            'response': response,
            'prompts': response.get('prompts', []),  # Assuming process_query returns prompts
            'intermediate_responses': response.get('intermediate_responses', []),  # Assuming process_query returns intermediate responses
            'intent': response.get('intent'),
            'intent_prompt': response.get('intent_prompt')
        })
        
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 