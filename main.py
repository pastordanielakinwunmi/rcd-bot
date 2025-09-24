import os
from flask import Flask, request, jsonify
import requests
import json

# Your bot token
BOT_TOKEN = "8207298018:AAHGHL0LFOc2JBSxyFCKC8hEfd3k3VSMfEs"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.route('/health')
def health():
    return {'status': 'healthy'}

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
        # Check if it's a message
        if 'message' in data:
            chat_id = data['message']['chat']['id']
            text = data['message'].get('text', '')
            
            if text == '/start':
                welcome_msg = """
Welcome to Real Christian Dating! 🙏

Find your Godly partner through faith-centered connections.

📱 App: Real Christian Dating
⛪ Focus: Strictly Christian Only  
🌍 Scope: Global
👥 Age Range: 18-75
                """
                send_telegram_message(chat_id, welcome_msg)
            elif text == '/help':
                send_telegram_message(chat_id, "Help: Contact support@realchristiandating.com")
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def send_telegram_message(chat_id, text):
    """Send message to Telegram"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    requests.post(url, json=payload)

@app.route('/')
def home():
    return "Real Christian Dating Bot is running!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
