import os
import logging
from flask import Flask, request, jsonify

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BRANDING = {
    "app_name": "Real Christian Dating",
    "app_short_name": "RCD",
    "logo_text": "RCD",
    "welcome_message": "Welcome to Real Christian Dating! 🙏\n\nFind your Godly partner through faith-centered connections. Let's get started!",
    "bot_description": "Strictly Christian dating app with advanced verification and USDT payments",
    "support_contact": "support@realchristiandating.com",
    "age_range": "18-75",
    "geographic_scope": "Global"
}

DATABASE_URL = os.getenv('DATABASE_URL', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8207298018:AAHGHL0LFOc2JBSxyFCKC8hEfd3k3VSMfEs')

# Initialize bot application once
bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

def init_database():
    """Initialize database tables"""
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        return False
        
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    age INTEGER,
                    gender VARCHAR(50),
                    location VARCHAR(255),
                    denomination VARCHAR(255),
                    church_attendance VARCHAR(100),
                    bio TEXT,
                    profile_photo_url TEXT,
                    verification_video_url TEXT,
                    is_verified BOOLEAN DEFAULT FALSE,
                    device_hash VARCHAR(255),
                    phone_hash VARCHAR(255),
                    is_banned BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS wallets (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    usdt_balance DECIMAL(15,8) DEFAULT 0.00000000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [InlineKeyboardButton("✨ Create Profile", callback_data='register_start')],
        [InlineKeyboardButton("💎 Premium Plans", callback_data='premium_info')],
        [InlineKeyboardButton("📖 Help & Support", callback_data='help')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
    {BRANDING['welcome_message']}
    
    📱 **App**: {BRANDING['app_name']}
    ⛪ **Focus**: Strictly Christian Only
    🌍 **Scope**: {BRANDING['geographic_scope']}
    👥 **Age Range**: {BRANDING['age_range']}
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = f"""
    🆘 **{BRANDING['app_name']} Help Center**
    
    **Getting Started:**
    /start - Begin your journey
    /register - Create your profile
    
    **Support:**
    Contact: {BRANDING['support_contact']}
    Age Range: {BRANDING['age_range']}
    Scope: {BRANDING['geographic_scope']}
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Add handlers once
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("help", help_command))

# Flask app
app = Flask(__name__)

@app.route('/health')
def health():
    return {'status': 'healthy', 'app': BRANDING['app_name']}

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates"""
    try:
        json_str = request.get_data().decode('UTF-8')
        update = Update.de_json(json_str, bot_app.bot)
        bot_app.update_queue.put_nowait(update)
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/')
def home():
    return {'message': f'{BRANDING["app_name"]} is running!'}

if __name__ == '__main__':
    # Initialize database
    if DATABASE_URL:
        init_database()
    
    # This will be handled by gunicorn in production
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
