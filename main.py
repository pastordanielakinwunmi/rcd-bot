import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')
        
        if text == '/start':
            msg = "Welcome to Real Christian Dating! 🙏\n\nYour bot is now working!"
            send_message(chat_id, msg)
        elif text == '/test':
            send_message(chat_id, "Test successful!")
    
    return jsonify({'ok': True})

def send_message(chat_id, text):
    token = "8207298018:AAHGHL0LFOc2JBSxyFCKC8hEfd3k3VSMfEs"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={'chat_id': chat_id, 'text': text})

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
