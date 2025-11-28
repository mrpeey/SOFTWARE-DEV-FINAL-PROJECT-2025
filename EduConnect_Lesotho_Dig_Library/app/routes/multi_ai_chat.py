from flask import Blueprint, request, jsonify
import os, requests

multi_ai_chat_bp = Blueprint('multi_ai_chat', __name__)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions'
HF_API_KEY = os.getenv('HF_API_KEY')
HF_API_URL = 'https://api-inference.huggingface.co/models/gpt2'  # Change model as needed

@multi_ai_chat_bp.route('/api/multi-ai-chat', methods=['POST'])
def multi_ai_chat():
    data = request.get_json()
    question = data.get('question', '')
    provider = data.get('provider', 'openai')  # 'openai' or 'huggingface'
    if not question:
        return jsonify({'answer': 'Kindly enter your question so I may assist you.'}), 400
    if provider == 'huggingface':
        headers = {
            'Authorization': f'Bearer {HF_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'inputs': f"Please answer professionally: {question}"
        }
        try:
            response = requests.post(HF_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            answer = result[0]['generated_text'] if isinstance(result, list) and 'generated_text' in result[0] else str(result)
            if not answer or answer.strip() == '':
                answer = "I'm sorry, I was unable to generate a response at this time. Please try again later."
            return jsonify({'answer': answer})
        except Exception as e:
            return jsonify({'answer': f"An error occurred while processing your request. Please try again later. ({str(e)})"}), 500
    else:
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'system', 'content': 'You are a helpful, professional library assistant. Respond in a clear, polite, and professional manner.'},
                {'role': 'user', 'content': question}
            ]
        }
        try:
            response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            answer = result['choices'][0]['message']['content']
            if not answer or answer.strip() == '':
                answer = "I'm sorry, I was unable to generate a response at this time. Please try again later."
            return jsonify({'answer': answer})
        except Exception as e:
            return jsonify({'answer': f"An error occurred while processing your request. Please try again later. ({str(e)})"}), 500
