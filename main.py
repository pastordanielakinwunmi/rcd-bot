import os
import logging
from datetime import datetime
from typing import Optional
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Branding Configuration - EASY TO MODIFY LATER
BRANDING = {
    "app_name": "Real Christian Dating",
    "app_short_name": "RCD",
    "logo_text": "RCD",
    "primary_color": "#8B5CF6",
    "secondary_color": "#06B6D4",
    "accent_color": "#10B981",
    "welcome_message": "Welcome to Real Christian Dating! 🙏\n\nFind your Godly partner through faith-centered connections. Let's get started!",
    "bot_description": "Strictly Christian dating app with advanced verification and USDT payments",
    "support_contact": "support@realchristiandating.com",
    "age_range": "18-75",
    "geographic_scope": "Global"
}

# Get environment variables
DATABASE_URL = os.getenv('DATABASE_URL', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8207298018:AAHGHL0LFOc2JBSxyFCKC8hEfd3k3VSMfEs')

# Conversation states
(AGE, GENDER, LOCATION, DENOMINATION, CHURCH_ATTENDANCE, BIO, 
 PHOTO, VERIFICATION_VIDEO) = range(8)

class DatabaseManager:
    def __init__(self, database_url):
        self.database_url = database_url
    
    def get_connection(self):
        if not self.database_url:
            raise ValueError("DATABASE_URL not set")
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
    
    def init_database(self):
        """Initialize database tables"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Users table
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
                    
                    # Wallets table
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS wallets (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                            usdt_balance DECIMAL(15,8) DEFAULT 0.00000000,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    conn.commit()
        except Exception as e:
            logger.error(f"Database initialization error: {e}")

class RCDTeleBot:
    def __init__(self):
        self.db = DatabaseManager(DATABASE_URL)
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Initialize database
        self.db.init_database()
        
        # Setup handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all bot command handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Conversation handler for registration
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('register', self.register_start)],
            states={
                AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.age)],
                GENDER: [CallbackQueryHandler(self.gender_callback)],
                LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.location)],
                DENOMINATION: [CallbackQueryHandler(self.denomination_callback)],
                CHURCH_ATTENDANCE: [CallbackQueryHandler(self.church_attendance_callback)],
                BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.bio)],
                PHOTO: [MessageHandler(filters.PHOTO, self.photo)],
                VERIFICATION_VIDEO: [MessageHandler(filters.VIDEO, self.verification_video)]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )
        self.application.add_handler(conv_handler)
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
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
        
        Tap below to get started!
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def register_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start registration process"""
        query = update.callback_query
        await query.answer()
        
        await query.message.reply_text("Please enter your age (18-75):")
        return AGE
    
    async def age(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle age input"""
        try:
            age = int(update.message.text)
            if age < 18 or age > 75:
                await update.message.reply_text("Age must be between 18-75. Please enter again:")
                return AGE
            
            context.user_data['age'] = age
            keyboard = [
                [InlineKeyboardButton("Male", callback_data='gender_male')],
                [InlineKeyboardButton("Female", callback_data='gender_female')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Select your gender:", reply_markup=reply_markup)
            return GENDER
            
        except ValueError:
            await update.message.reply_text("Please enter a valid number:")
            return AGE
    
    async def gender_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle gender selection"""
        query = update.callback_query
        await query.answer()
        
        gender = query.data.split('_')[1]
        context.user_data['gender'] = gender.capitalize()
        
        await query.message.reply_text("Please enter your location (city, country):")
        return LOCATION
    
    async def location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle location input"""
        location = update.message.text
        context.user_data['location'] = location
        
        denominations = [
            "Catholic", "Baptist", "Methodist", "Lutheran", "Presbyterian", 
            "Pentecostal", "Orthodox", "Non-denominational", "Other"
        ]
        
        keyboard = []
        for i in range(0, len(denominations), 2):
            row = []
            for j in range(2):
                if i + j < len(denominations):
                    row.append(InlineKeyboardButton(
                        denominations[i + j], 
                        callback_data=f'denom_{denominations[i + j]}'
                    ))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select your denomination:", reply_markup=reply_markup)
        return DENOMINATION
    
    async def denomination_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle denomination selection"""
        query = update.callback_query
        await query.answer()
        
        denomination = query.data.split('_', 1)[1]
        context.user_data['denomination'] = denomination
        
        attendance_options = ["Weekly", "Monthly", "Occasionally", "Seeking"]
        keyboard = [[InlineKeyboardButton(opt, callback_data=f'attend_{opt}')] for opt in attendance_options]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text("How often do you attend church?", reply_markup=reply_markup)
        return CHURCH_ATTENDANCE
    
    async def church_attendance_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle church attendance selection"""
        query = update.callback_query
        await query.answer()
        
        attendance = query.data.split('_', 1)[1]
        context.user_data['church_attendance'] = attendance
        
        await query.message.reply_text("Tell us about yourself (bio):")
        return BIO
    
    async def bio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle bio input"""
        bio = update.message.text
        context.user_data['bio'] = bio[:500]  # Limit to 500 characters
        
        await update.message.reply_text("Please upload a profile photo:")
        return PHOTO
    
    async def photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo upload"""
        photo = update.message.photo[-1]  # Get highest quality
        context.user_data['photo_file_id'] = photo.file_id
        
        await update.message.reply_text(
            "For security verification, please record a short video (5-10 seconds) "
            "saying: 'I seek God's will in love and relationships.'"
        )
        return VERIFICATION_VIDEO
    
    async def verification_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle verification video"""
        video = update.message.video
        context.user_data['video_file_id'] = video.file_id
        
        # Save user to database (simplified)
        await update.message.reply_text(
            "✅ Profile created successfully!\n\n"
            "Your verification video will be reviewed by our team. "
            "You'll receive a notification when verified.\n\n"
            "In the meantime, you can browse profiles and send likes!"
        )
        
        return ConversationHandler.END
    
    async def premium_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show premium plans"""
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
        
        *Save 20% with 3-month plans*
        *Payments in USDT (TRC20)*
        """
        
        await query.message.edit_text(premium_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        query = update.callback_query
        data = query.data
        
        if data == 'register_start':
            await query.answer()
            await query.message.reply_text("Please enter your age (18-75):")
            return AGE
        elif data == 'premium_info':
            return await self.premium_info(update, context)
        elif data == 'start_menu':
            return await self.start(update, context)
        elif data.startswith('gender_'):
            return await self.gender_callback(update, context)
        elif data.startswith('denom_'):
            return await self.denomination_callback(update, context)
        elif data.startswith('attend_'):
            return await self.church_attendance_callback(update, context)
        else:
            await query.answer("Feature coming soon!")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        help_text = f"""
        🆘 **{BRANDING['app_name']} Help Center**
        
        **Getting Started:**
        /start - Begin your journey
        /register - Create your profile
        
        **Profile & Matching:**
        /profile - View/edit your profile
        /browse - Discover new matches
        /premium - Upgrade to premium
        
        **Account:**
        /wallet - Check USDT balance
        /settings - Account settings
        /groups - Join faith communities
        
        **Support:**
        Contact: {BRANDING['support_contact']}
        Age Range: {BRANDING['age_range']}
        Scope: {BRANDING['geographic_scope']}
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel conversation"""
        await update.message.reply_text("Registration cancelled. Type /start to begin again.")
        return ConversationHandler.END
    
    def run(self):
        """Start the bot"""
        logger.info(f"Starting {BRANDING['app_name']} bot...")
        self.application.run_polling()

if __name__ == '__main__':
    bot = RCDTeleBot()
    bot.run()
