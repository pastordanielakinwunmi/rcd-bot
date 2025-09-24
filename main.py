import os
import logging
from flask import Flask, request, jsonify

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
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

# Conversation states
(AGE, GENDER, LOCATION, DENOMINATION, CHURCH_ATTENDANCE, BIO, 
 PHOTO, VERIFICATION_VIDEO) = range(8)

# Global bot application
bot_app = None

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

async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show premium plans"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🥇 Gold - 15 USDT/month", callback_data='premium_gold')],
        [InlineKeyboardButton("🏆 Platinum - 30 USDT/month", callback_data='premium_platinum')],
        [InlineKeyboardButton("⬅️ Back", callback_data='start_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    premium_text = f"""
    💎 **{BRANDING['app_name']} Premium Plans**
    
    **🥇 Gold Tier - 15 USDT/month**
    • Unlimited likes & matches
    • See who liked you
    • Video & voice calls
    • Faith-based group access
    • Daily devotion matches
    
    **🏆 Platinum Tier - 30 USDT/month**
    • All Gold features
    • Exclusive event invites
    • Background check discount
    • Priority support
    • Enhanced profile visibility
    """
    
    await query.message.edit_text(premium_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    data = query.data
    
    if data == 'premium_info':
        return await premium_info(update, context)
    elif data == 'start_menu':
        return await start(update, context)
    else:
        await query.answer("Feature coming soon!")

def setup_bot():
    """Initialize and setup the bot application"""
    global bot_app
    if bot_app is not None:
        return bot_app
        
    bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CallbackQueryHandler(button_handler))
    
    return bot_app

# Flask app
app = Flask(__name__)

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return {'status': 'healthy', 'app': BRANDING['app_name']}

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates"""
    global bot_app
    if bot_app is None:
        setup_bot()
    
    if bot_app is None:
        return jsonify({'error': 'Bot initialization failed'}), 500
    
    # Get the update from Telegram
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json_str, bot_app.bot)
    
    # Process the update asynchronously
    try:
        bot_app.update_queue.put_nowait(update)
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return jsonify({'error': 'Failed to process update'}), 500

@app.route('/setwebhook')
def set_webhook():
    """Set the Telegram webhook (call this once after deployment)"""
    try:
        global bot_app
        if bot_app is None:
            bot_app = setup_bot()
        
        # Get the webhook URL
        render_url = os.getenv('RENDER_EXTERNAL_URL', 'https://rcd-bot.onrender.com')
        webhook_url = f"{render_url}/webhook"
        
        # Set webhook
        bot_app.bot.set_webhook(url=webhook_url)
        
        return jsonify({
            'status': 'webhook set successfully',
            'webhook_url': webhook_url
        })
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return jsonify({'error': f'Failed to set webhook: {str(e)}'}), 500

@app.route('/')
def home():
    """Home page"""
    return {'message': f'{BRANDING["app_name"]} is running!'}

if __name__ == '__main__':
    # Initialize database
    if DATABASE_URL:
        init_database()
    else:
        logger.warning("DATABASE_URL not set - database features will be disabled")
    
    # Get port from environment (Render sets this)
    port = int(os.environ.get('PORT', 10000))
    
    # Start Flask app
    app.run(host='0.0.0.0', port=port)
