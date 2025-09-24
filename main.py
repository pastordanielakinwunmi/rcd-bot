import os
import logging
from flask import Flask, request, jsonify

# Only import what we need for webhook processing
from telegram import Update
import telegram.ext

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8207298018:AAHGHL0LFOc2JBSxyFCKC8hEfd3k3VSMfEs')

# Create bot instance
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

app = Flask(__name__)

@app.route('/health')
def health():
    return {'status': 'healthy', 'app': 'Real Christian Dating'}

@app.route('/webhook', methods=['POST'])
def webhook():
    """Simple webhook that just acknowledges Telegram messages"""
    try:
        # Get the update
        json_str = request.get_data().decode('UTF-8')
        update = Update.de_json(json_str, bot)
        
        # Simple response for /start command
        if update.message and update.message.text == '/start':
            welcome_message = """
Welcome to Real Christian Dating! 🙏

Find your Godly partner through faith-centered connections.

📱 App: Real Christian Dating
⛪ Focus: Strictly Christian Only  
🌍 Scope: Global
👥 Age Range: 18-75

Type /help for assistance.
            """
            bot.send_message(chat_id=update.message.chat_id, text=welcome_message)
        
        elif update.message and update.message.text == '/help':
            bot.send_message(chat_id=update.message.chat_id, text="Help: Contact support@realchristiandating.com")
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/')
def home():
    return {'message': 'Real Christian Dating Bot is running!'}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
