from flask import Blueprint, request, jsonify, session, render_template
import os, requests, openai, logging, json
from app.models.book import Book
from app.models.review import BookReview
from app.models.user import User
from app import db
from flask_login import login_required, current_user

ai_chat_bp = Blueprint('ai_chat', __name__)

openai.api_key = os.getenv('OPENAI_API_KEY', 'your-openai-key')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'your-gemini-key')
AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai')  # 'openai' or 'gemini'

# Setup secure logger for analytics
logger = logging.getLogger('ai_chat_analytics')
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.FileHandler('logs/ai_chat_analytics.log')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)

def get_ai_response(messages):
    if AI_PROVIDER == 'openai':
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=256,
            temperature=0.7
        )
        return response.choices[0].message['content'].strip()
    elif AI_PROVIDER == 'gemini':
        # Stub: Replace with Gemini API call
        return "Gemini AI response (stub)."
    else:
        return "No valid AI provider configured."

@ai_chat_bp.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    data = request.get_json()
    question = data.get('question', '')
    provider = data.get('provider', 'openai')  # 'openai' or 'huggingface'
    if not question:
        return jsonify({'answer': 'Kindly enter your question so I may assist you.'}), 400

    if provider == 'huggingface':
        HF_API_KEY = os.getenv('HF_API_KEY')
        HF_API_URL = 'https://api-inference.huggingface.co/models/gpt2'  # Change model as needed
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
            # Ensure professional fallback
            if not answer or answer.strip() == '':
                answer = "I'm sorry, I was unable to generate a response at this time. Please try again later."
            return jsonify({'answer': answer})
        except Exception as e:
            return jsonify({'answer': f"An error occurred while processing your request. Please try again later. ({str(e)})"}), 500
    else:
        # Default to OpenAI
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_api_url = os.getenv("OPENAI_API_URL")
        headers = {
            'Authorization': f'Bearer {openai_api_key}',
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
            response = requests.post(openai_api_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            answer = result['choices'][0]['message']['content']
            if not answer or answer.strip() == '':
                answer = "I'm sorry, I was unable to generate a response at this time. Please try again later."
            return jsonify({'answer': answer})
        except Exception as e:
            return jsonify({'answer': f"An error occurred while processing your request. Please try again later. ({str(e)})"}), 500

@ai_chat_bp.route('/ai_chat', methods=['POST'])
def ai_chat_search():
    data = request.get_json()
    user_query = data.get('query', '')
    user_id = getattr(current_user, 'id', 'anonymous')
    # Maintain chat history in session
    if 'ai_chat_history' not in session:
        session['ai_chat_history'] = []
    session['ai_chat_history'].append({'role': 'user', 'content': user_query})
    # Search books, reviews, categories, and static pages for context
    books = Book.query.filter(Book.title.ilike(f'%{user_query}%')).limit(3).all()
    reviews = BookReview.query.filter(BookReview.review_text.ilike(f'%{user_query}%')).limit(3).all()
    categories = db.session.query(Book.category_id, Book.category).filter(Book.category.ilike(f'%{user_query}%')).limit(2).all()
    # Optionally, search static pages (e.g., about, FAQ)
    static_context = "Library hours: 8am-6pm. Contact: info@educonnect.ls. Location: Maseru, Lesotho."
    context = []
    for book in books:
        context.append(f"Book: {book.title} by {book.author}. {book.description}")
    for review in reviews:
        context.append(f"Review: {review.review_text}")
    for cat_id, cat_name in categories:
        context.append(f"Category: {cat_name}")
    context.append(static_context)
    context_str = '\n'.join(context)
    # Build chat history for AI
    history = session['ai_chat_history'][-5:]  # Last 5 messages for brevity
    messages = [
        {"role": "system", "content": "You are the Library AI. Use the following context from the library website to answer the user's question."},
        {"role": "system", "content": f"Context:\n{context_str}"}
    ]
    for msg in history:
        messages.append(msg)
    # Call OpenAI Chat API (can be replaced with Gemini, etc.)
    answer = get_ai_response(messages)
    session['ai_chat_history'].append({'role': 'assistant', 'content': answer})
    session.modified = True
    actions = []
    for book in Book.query.filter(Book.title.ilike(f'%{answer}%')).limit(1):
        actions.append({
            'type': 'reserve',
            'label': f'Reserve "{book.title}"',
            'book_id': book.id
        })
        actions.append({
            'type': 'view',
            'label': f'View "{book.title}"',
            'book_id': book.id
        })
    # Log analytics securely
    logger.info(f"User: {user_id} | Query: {user_query} | Answer: {answer[:100]} | Actions: {actions}")
    return jsonify({'answer': answer, 'actions': actions})

@ai_chat_bp.route('/admin/ai_chat_logs')
@login_required
def ai_chat_logs():
    if not getattr(current_user, 'is_admin', False):
        return "Unauthorized", 403
    # For demo: get all chat logs from session (in production, use DB)
    logs = session.get('ai_chat_history', [])
    return jsonify({'logs': logs})

@ai_chat_bp.route('/admin/ai_chat_analytics')
@login_required
def ai_chat_analytics():
    if not getattr(current_user, 'is_admin', False):
        return "Unauthorized", 403
    log_path = 'logs/ai_chat_analytics.log'
    analytics = []
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            for line in f:
                # Parse log line
                try:
                    parts = line.strip().split('|')
                    analytics.append({
                        'timestamp': parts[0].split(' ')[0],
                        'user': parts[1].split(':')[1].strip(),
                        'query': parts[2].split(':')[1].strip(),
                        'answer': parts[3].split(':')[1].strip(),
                        'actions': parts[4].split(':')[1].strip()
                    })
                except Exception:
                    continue
    return jsonify({'analytics': analytics})

@ai_chat_bp.route('/admin/ai_chat_analytics_dashboard')
@login_required
def ai_chat_analytics_dashboard():
    if not getattr(current_user, 'is_admin', False):
        return "Unauthorized", 403
    return render_template('admin/ai_chat_analytics.html')
