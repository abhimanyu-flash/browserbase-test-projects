import os
import re
import subprocess
from flask import Flask, request, jsonify
import requests
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

ORDER_SERVER = os.environ.get('ORDER_SERVER', 'http://localhost:3000/login')
AMAZON_EMAIL = os.environ.get('AMAZON_EMAIL', 'your-email@domain.com')
AMAZON_PASSWORD = os.environ.get('AMAZON_PASSWORD', 'your-password')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY
print(f"OpenAI API Key loaded: {'Yes (first 5 chars: ' + OPENAI_API_KEY[:5] + '...)' if OPENAI_API_KEY else 'No'}")
print(f"Amazon Email loaded: {'Yes' if AMAZON_EMAIL != 'your-email@domain.com' else 'No'}")
print(f"Amazon Password loaded: {'Yes' if AMAZON_PASSWORD != 'your-password' else 'No'}")


from flask import send_from_directory

app = Flask(__name__, static_folder='public')

# --- TOOL WRAPPERS --- #
def order_product(email, password, url):
    resp = requests.post(ORDER_SERVER, json={
        'email': email,
        'password': password,
        'productUrl': url
    })
    return resp.text

def cancel_product(product):
    proc = subprocess.Popen(
        ['node', 'amazoncancel.mjs', product],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    output, _ = proc.communicate()
    return output.decode('utf-8')

# --- LangGraph workflow setup ---
def detect_intent_node(state):
    message = state.get('input', '')
    print(f"\n==== DETECT INTENT NODE CALLED ====\nUser input: {message}")
    
    url_match = re.search(r'https?://(www\.)?amazon\.[a-z.]+[^\s]*', message, re.I)
    if url_match:
        print(f"Detected ORDER intent with URL: {url_match.group(0)}")
        return {'intent': 'order', 'url': url_match.group(0)}
        
    if 'cancel' in message.lower():
        prod_match = re.search(r'cancel\s+(my\s+order\s+for\s+)?(.+)', message, re.I)
        if prod_match and prod_match.group(2):
            product = prod_match.group(2).strip()
            print(f"Detected CANCEL intent with product: {product}")
            return {'intent': 'cancel', 'product': product}
        print("Detected CANCEL intent without product")
        return {'intent': 'cancel', 'product': ''}
        
    print("Detected CHAT intent - routing to chat node")
    return {'intent': 'chat'}

def order_node(state):
    url = state.get('url')
    result = order_product(AMAZON_EMAIL, AMAZON_PASSWORD, url)
    return {'response': f"Ordering this product: {url}\n{result}"}

def cancel_node(state):
    product = state.get('product')
    if not product:
        return {'response': 'Please specify the product you want to cancel.'}
    result = cancel_product(product)
    return {'response': result}

def chat_node(state):
    user_input = state.get('input', '')
    
    print(f"\n==== CHAT NODE CALLED ====\nUser input: {user_input}")
    print(f"OpenAI API Key status: {'Set (first 5 chars: ' + OPENAI_API_KEY[:5] + '...)' if OPENAI_API_KEY else 'Not set'}")
    
    # If OpenAI API key is not set, use default response
    if not OPENAI_API_KEY:
        print("No OpenAI API key found, using default response")
        return {'response': "I'm your Amazon assistant. Send me a product link to order, or ask to cancel an order."}
    
    try:
        print("Attempting to call OpenAI API...")
        # Create a system prompt that defines the assistant's behavior
        system_prompt = """
        You are an Amazon shopping assistant chatbot. You can help users order products from Amazon 
        or cancel their existing orders. Be friendly, helpful, and concise.
        
        You can:
        1. Process Amazon product links to order products
        2. Cancel orders when users specify the product name
        3. Answer general questions about Amazon shopping
        
        If the user sends an Amazon product link, tell them you'll order it for them.
        If they ask to cancel an order, ask for the product name if they haven't provided it.
        
        Keep your responses brief and conversational.
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        # Extract the assistant's response
        ai_response = response.choices[0].message.content
        print(f"OpenAI response received: {ai_response[:50]}...")
        return {'response': ai_response}
    except Exception as e:
        print(f"ERROR calling OpenAI API: {e}")
        import traceback
        traceback.print_exc()
        return {'response': "I'm your Amazon assistant. Send me a product link to order, or ask to cancel an order."}

from typing import TypedDict, Optional

class ChatState(TypedDict, total=False):
    input: str
    intent: str
    url: Optional[str]
    product: Optional[str]
    response: Optional[str]

# Build the workflow graph
state_schema = ChatState

graph = StateGraph(state_schema)
graph.add_node('detect_intent', detect_intent_node)
graph.add_node('order', order_node)
graph.add_node('cancel', cancel_node)
graph.add_node('chat', chat_node)

def route(state):
    intent = state.get('intent')
    if intent == 'order':
        return 'order'
    elif intent == 'cancel':
        return 'cancel'
    else:
        return 'chat'

graph.add_conditional_edges(
    'detect_intent',
    route,
    {'order': 'order', 'cancel': 'cancel', 'chat': 'chat'}
)
graph.add_edge('order', '__end__')
graph.add_edge('cancel', '__end__')
graph.add_edge('chat', '__end__')
graph.set_entry_point('detect_intent')
workflow = graph.compile()

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    state = {'input': message}
    result = workflow.invoke(state)
    return jsonify({'response': result.get('response', '')})

# Static file handler must be defined after all API endpoints!
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(port=5001, debug=True)
