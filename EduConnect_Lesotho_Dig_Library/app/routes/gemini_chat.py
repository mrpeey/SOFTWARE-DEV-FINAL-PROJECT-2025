from flask import Blueprint, request, jsonify
import os
import requests

gemini_chat_bp = Blueprint('gemini_chat', __name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Set this in your environment
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent'

@gemini_chat_bp.route('/api/gemini-chat', methods=['POST'])
def gemini_chat():
    data = request.get_json()
    question = data.get('question', '')
    if not question:
        return jsonify({'answer': 'Please enter a question.'}), 400
    headers = {
        'Content-Type': 'application/json',
    }
    payload = {
        'contents': [
            {'parts': [{'text': question}]}
        ]
    }
    try:
        response = requests.post(f'{GEMINI_API_URL}?key={GEMINI_API_KEY}', headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        answer = result['candidates'][0]['content']['parts'][0]['text'] if 'candidates' in result else 'No answer.'
        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'answer': f'Error: {str(e)}'}), 500
