from flask import Blueprint, request, jsonify
import os, requests

summarize_search_bp = Blueprint('summarize_search', __name__)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions'

@summarize_search_bp.route('/api/summarize', methods=['POST'])
def summarize():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({'summary': 'No text provided.'}), 400
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'gpt-3.5-turbo',
        'messages': [
            {'role': 'user', 'content': f'Summarize this: {text}'}
        ]
    }
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        summary = result['choices'][0]['message']['content']
        return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'summary': f'Error: {str(e)}'}), 500

@summarize_search_bp.route('/api/semantic-search', methods=['POST'])
def semantic_search():
    data = request.get_json()
    query = data.get('query', '')
    # For demo, return mock results. Integrate with real search API or embeddings for production.
    results = [f"Result for '{query}' #1", f"Result for '{query}' #2"]
    return jsonify({'results': results})
