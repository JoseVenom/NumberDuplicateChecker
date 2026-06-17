import os
import json
import csv
import io
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import logging
from google.oauth2.service_account import Credentials
from google.cloud import drive_v3

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
UPLOAD_CSV, REPORT_REPLY = range(2)

# Global variables
original_numbers = set()
reply_data = {}
csv_uploaded = False
bot_running = True
ADMIN_IDS = [123456789]  # Replace with your Telegram user ID
DRIVE_FOLDER_ID = "your_folder_id_here"  # Replace with your Google Drive folder ID

class GoogleDriveManager:
    """Manage Google Drive uploads"""
    
    def __init__(self, credentials_file='credentials.json'):
        self.credentials_file = credentials_file
        self.service = None
        self.initialize()
    
    def initialize(self):
        """Initialize Google Drive service"""
        try:
            if os.path.exists(self.credentials_file):
                creds = Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                self.service = drive_v3.build('drive', 'v3', credentials=creds)
                logger.info("✅ Google Drive connected")
            else:
                logger.warning("⚠️ credentials.json not found. Google Drive upload disabled")
        except Exception as e:
            logger.error(f"❌ Google Drive error: {str(e)}")
    
    def upload_file(self, file_path, file_name, folder_id=None):
        """Upload file to Google Drive"""
        try:
            if not self.service:
                logger.warning("Google Drive not initialized")
                return None
            
            file_metadata = {
                'name': file_name,
                'parents': [folder_id or DRIVE_FOLDER_ID]
            }
            
            media = drive_v3.MediaFileUpload(file_path)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            logger.info(f"✅ Uploaded {file_name} to Google Drive")
            return file.get('webViewLink')
        except Exception as e:
            logger.error(f"❌ Upload error: {str(e)}")
            return None
    
    def upload_from_string(self, content, file_name, folder_id=None):
        """Upload text content as file to Google Drive"""
        try:
            if not self.service:
                return None
            
            # Create temporary file
            temp_path = f"temp_{file_name}"
            with open(temp_path, 'w') as f:
                f.write(content)
            
            file_metadata = {
                'name': file_name,
                'parents': [folder_id or DRIVE_FOLDER_ID]
            }
            
            media = drive_v3.MediaFileUpload(temp_path)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            os.remove(temp_path)
            logger.info(f"✅ Uploaded {file_name} to Google Drive")
            return file.get('webViewLink')
        except Exception as e:
            logger.error(f"❌ Upload error: {str(e)}")
            return None

# Initialize Google Drive
drive_manager = GoogleDriveManager()

async def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command"""
    user_id = update.message.from_user.id
    is_admin_user = await is_admin(user_id)
    
    if is_admin_user:
        keyboard = [
            [InlineKeyboardButton("📤 Upload CSV", callback_data='upload_csv')],
            [InlineKeyboardButton("🤖 Start Bot", callback_data='start_bot')],
            [InlineKeyboardButton("⏹️ Stop Bot", callback_data='stop_bot')],
            [InlineKeyboardButton("📝 Report Reply", callback_data='report_reply')],
            [InlineKeyboardButton("✅ Verify Replies", callback_data='verify')],
            [InlineKeyboardButton("📥 Export Report", callback_data='export')],
            [InlineKeyboardButton("📊 Show Summary", callback_data='summary')],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("📝 Report Reply", callback_data='report_reply')],
            [InlineKeyboardButton("📊 Show Summary", callback_data='summary')],
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome = "🤖 *Customer Response Tracker Bot*\n\n"
    if is_admin_user:
        welcome += "👑 Admin Mode\n\n"
    welcome += "Upload CSV with customer numbers, track & verify member replies.\n\n"
    
    await update.message.reply_text(
        welcome + "Select an option:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle all callback queries"""
    query = update.callback_query
    user_id = query.from_user.id
    is_admin_user = await is_admin(user_id)
    
    if query.data == 'upload_csv':
        if not is_admin_user:
            await query.answer("❌ Admin only!", show_alert=True)
            return
        await upload_csv_handler(update, context)
        return UPLOAD_CSV
    
    elif query.data == 'report_reply':
        await report_reply_handler(update, context)
        return REPORT_REPLY
    
    elif query.data == 'verify':
        if not is_admin_user:
            await query.answer("❌ Admin only!", show_alert=True)
            return
        await verify_handler(update, context)
    
    elif query.data == 'export':
        if not is_admin_user:
            await query.answer("❌ Admin only!", show_alert=True)
            return
        await export_handler(update, context)
    
    elif query.data == 'summary':
        await summary_handler(update, context)
    
    elif query.data == 'start_bot':
        if not is_admin_user:
            await query.answer("❌ Admin only!", show_alert=True)
            return
        global bot_running
        bot_running = True
        await query.answer("✅ Bot Started!", show_alert=True)
        await query.edit_message_text("✅ Bot is now RUNNING")
    
    elif query.data == 'stop_bot':
        if not is_admin_user:
            await query.answer("❌ Admin only!", show_alert=True)
            return
        bot_running = False
        await query.answer("⏹️ Bot Stopped!", show_alert=True)
        await query.edit_message_text("⏹️ Bot is now STOPPED")

async def upload_csv_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user to upload CSV"""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text="📤 Send me the CSV file with customer numbers\n\n"
        "CSV Format:\n"
        "`Customer Number`\n"
        "`94771234567`\n"
        "`94771234568`\n"
        "`94771234569`",
        parse_mode='Markdown'
    )
    return UPLOAD_CSV

async def handle_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle CSV file upload"""
    global original_numbers, csv_uploaded
    
    if update.message.document is None:
        await update.message.reply_text("❌ Please send a CSV file")
        return UPLOAD_CSV
    
    try:
        file = await update.message.document.get_file()
        file_path = f"uploads/{update.message.document.file_id}.csv"
        os.makedirs("uploads", exist_ok=True)
        await file.download_to_drive(file_path)
        
        original_numbers.clear()
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    number = row[0].strip()
                    if number and number.lower() != 'customer number':
                        original_numbers.add(number)
        
        csv_uploaded = True
        
        # Save to local database
        save_database()
        
        # Upload to Google Drive
        gdrive_link = drive_manager.upload_file(
            file_path,
            f"CustomerList_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        message = (
            f"✅ CSV Uploaded Successfully!\n\n"
            f"📊 Total Numbers: {len(original_numbers)}\n\n"
            f"Numbers:\n{', '.join(sorted(list(original_numbers)[:10]))}"
            f"{'...' if len(original_numbers) > 10 else ''}"
        )
        
        if gdrive_link:
            message += f"\n\n📁 Saved to Drive: [Link]({gdrive_link})"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    
    return ConversationHandler.END

async def report_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user to report reply"""
    global csv_uploaded
    
    await update.callback_query.answer()
    
    if not csv_uploaded:
        await update.callback_query.edit_message_text(
            text="⚠️ CSV not uploaded yet! Ask admin to upload CSV first."
        )
        return ConversationHandler.END
    
    await update.callback_query.edit_message_text(
        text="📝 Send reply in format:\n\n"
        "`94771234567 | John | @john_telegram | Manager | 1`\n\n"
        "Or detailed format:\n"
        "`Nick Name: John`\n"
        "`Customer Number: 94771234567`\n"
        "`User ID: @john`\n"
        "`Position: Manager`\n"
        "`Serial: 1`\n"
        "`Name: John Doe`",
        parse_mode='Markdown'
    )
    return REPORT_REPLY

async def handle_reply_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reply submission"""
    global reply_data, original_numbers, bot_running
    
    if not bot_running:
        await update.message.reply_text("⏹️ Bot is stopped. Contact admin.")
        return REPORT_REPLY
    
    text = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"
    
    reply_info = parse_reply(text)
    
    if not reply_info or 'customer_number' not in reply_info:
        await update.message.reply_text(
            "❌ Invalid format! Use:\n`94771234567 | John | @user_id | Manager | 1`",
            parse_mode='Markdown'
        )
        return REPORT_REPLY
    
    customer_num = reply_info['customer_number']
    
    # Check if in original list
    in_list = customer_num in original_numbers
    status = "✅ IN LIST" if in_list else "❌ NOT IN LIST"
    
    if customer_num not in reply_data:
        reply_data[customer_num] = []
    
    # Check duplicates
    duplicate = any(r['user_id'] == user_id for r in reply_data[customer_num])
    
    reply_data[customer_num].append({
        'user_id': user_id,
        'username': username,
        'data': reply_info,
        'timestamp': datetime.now().isoformat(),
        'in_list': in_list
    })
    
    # Save to database
    save_database()
    
    message = (
        f"{status}\n\n"
        f"Customer Number: `{customer_num}`\n"
        f"Nick Name: {reply_info.get('nick_name', 'N/A')}\n"
        f"User ID: {reply_info.get('user_id', 'N/A')}"
    )
    
    if duplicate:
        message += "\n\n⚠️ *Duplicate Report!* You already reported this."
    else:
        message += "\n\n✅ Reply saved successfully!"
    
    await update.message.reply_text(message, parse_mode='Markdown')
    
    return REPORT_REPLY

async def verify_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verify all replies"""
    global original_numbers, reply_data
    
    await update.callback_query.answer()
    
    if not original_numbers:
        await update.callback_query.edit_message_text(
            text="⚠️ No CSV uploaded yet!"
        )
        return
    
    matched = set(reply_data.keys()) & original_numbers
    not_matched = set(reply_data.keys()) - original_numbers
    missing = original_numbers - set(reply_data.keys())
    
    message = (
        f"*📊 Verification Report*\n\n"
        f"✅ *Matched:* {len(matched)}\n"
        f"❌ *Not in List:* {len(not_matched)}\n"
        f"⏳ *Missing Replies:* {len(missing)}\n"
        f"📈 *Total Original:* {len(original_numbers)}\n"
        f"📝 *Total Replies:* {sum(len(v) for v in reply_data.values())}\n"
    )
    
    if not_matched:
        message += f"\n*❌ Not Matched Numbers:*\n"
        for num in sorted(list(not_matched)[:10]):
            count = len(reply_data[num])
            message += f"• `{num}` ({count} reports)\n"
        if len(not_matched) > 10:
            message += f"... and {len(not_matched) - 10} more\n"
    
    if missing:
        message += f"\n*⏳ Missing Replies:*\n"
        for num in sorted(list(missing)[:10]):
            message += f"• `{num}`\n"
        if len(missing) > 10:
            message += f"... and {len(missing) - 10} more\n"
    
    await update.callback_query.edit_message_text(
        text=message,
        parse_mode='Markdown'
    )

async def export_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Export report to Google Drive"""
    global original_numbers, reply_data
    
    await update.callback_query.answer()
    
    try:
        # Create matched report
        matched_csv = "Customer Number,Nick Name,User ID,Position,Serial,Name,Reporter,Timestamp\n"
        for num in sorted(original_numbers & set(reply_data.keys())):
            for reply in reply_data[num]:
                data = reply['data']
                matched_csv += (
                    f"{num},"
                    f"{data.get('nick_name', '')},"
                    f"{data.get('user_id', '')},"
                    f"{data.get('position', '')},"
                    f"{data.get('serial', '')},"
                    f"{data.get('name', '')},"
                    f"{reply['username']},"
                    f"{reply['timestamp']}\n"
                )
        
        # Create not matched report
        not_matched_csv = "Customer Number,Nick Name,User ID,Position,Serial,Name,Reporter,Timestamp,Status\n"
        for num in sorted(set(reply_data.keys()) - original_numbers):
            for reply in reply_data[num]:
                data = reply['data']
                not_matched_csv += (
                    f"{num},"
                    f"{data.get('nick_name', '')},"
                    f"{data.get('user_id', '')},"
                    f"{data.get('position', '')},"
                    f"{data.get('serial', '')},"
                    f"{data.get('name', '')},"
                    f"{reply['username']},"
                    f"{reply['timestamp']},"
                    f"NOT IN ORIGINAL LIST\n"
                )
        
        # Create missing report
        missing_csv = "Customer Number\n"
        for num in sorted(original_numbers - set(reply_data.keys())):
            missing_csv += f"{num}\n"
        
        # Create summary
        summary_text = (
            f"CUSTOMER RESPONSE REPORT\n"
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"SUMMARY:\n"
            f"Total Original Numbers: {len(original_numbers)}\n"
            f"Matched Responses: {len(original_numbers & set(reply_data.keys()))}\n"
            f"Not Matched: {len(set(reply_data.keys()) - original_numbers)}\n"
            f"Missing Replies: {len(original_numbers - set(reply_data.keys()))}\n"
            f"Total Response Reports: {sum(len(v) for v in reply_data.values())}\n"
        )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Upload to Google Drive
        link1 = drive_manager.upload_from_string(
            matched_csv,
            f"Matched_Responses_{timestamp}.csv"
        )
        link2 = drive_manager.upload_from_string(
            not_matched_csv,
            f"NotMatched_Responses_{timestamp}.csv"
        )
        link3 = drive_manager.upload_from_string(
            missing_csv,
            f"Missing_Replies_{timestamp}.csv"
        )
        link4 = drive_manager.upload_from_string(
            summary_text,
            f"Summary_Report_{timestamp}.txt"
        )
        
        message = (
            f"✅ *Export Complete!*\n\n"
            f"📊 Reports Generated:\n"
            f"1. ✅ Matched Responses\n"
            f"2. ❌ Not Matched\n"
            f"3. ⏳ Missing Replies\n"
            f"4. 📋 Summary\n\n"
            f"📁 Saved to Google Drive"
        )
        
        await update.callback_query.edit_message_text(
            text=message,
            parse_mode='Markdown'
        )
        
        # Send files to user
        if any([link1, link2, link3, link4]):
            await update.callback_query.message.reply_text(
                f"📥 *Download Links:*\n\n"
                f"✅ [Matched]({link1 or 'N/A'})\n"
                f"❌ [Not Matched]({link2 or 'N/A'})\n"
                f"⏳ [Missing]({link3 or 'N/A'})\n"
                f"📋 [Summary]({link4 or 'N/A'})",
                parse_mode='Markdown'
            )
        
    except Exception as e:
        await update.callback_query.edit_message_text(
            text=f"❌ Export error: {str(e)}"
        )

async def summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show summary"""
    global original_numbers, reply_data
    
    await update.callback_query.answer()
    
    matched_count = len(original_numbers & set(reply_data.keys()))
    not_matched_count = len(set(reply_data.keys()) - original_numbers)
    missing_count = len(original_numbers - set(reply_data.keys()))
    
    match_rate = round(matched_count/len(original_numbers)*100, 1) if original_numbers else 0
    
    message = (
        f"*📋 Summary Report*\n\n"
        f"📤 Original Numbers: {len(original_numbers)}\n"
        f"✅ Matched Replies: {matched_count}\n"
        f"❌ Not Matched: {not_matched_count}\n"
        f"⏳ Missing: {missing_count}\n"
        f"📝 Total Reports: {sum(len(v) for v in reply_data.values())}\n\n"
        f"📊 *Match Rate:* {match_rate}%"
    )
    
    await update.callback_query.edit_message_text(
        text=message,
        parse_mode='Markdown'
    )

def parse_reply(text: str) -> dict:
    """Parse reply in multiple formats"""
    reply_info = {}
    
    if '|' in text:
        parts = [p.strip() for p in text.split('|')]
        if len(parts) >= 1:
            reply_info['customer_number'] = parts[0]
        if len(parts) >= 2:
            reply_info['nick_name'] = parts[1]
        if len(parts) >= 3:
            reply_info['user_id'] = parts[2]
        if len(parts) >= 4:
            reply_info['position'] = parts[3]
        if len(parts) >= 5:
            reply_info['serial'] = parts[4]
        return reply_info
    
    lines = text.split('\n')
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower().replace(' ', '_')
            value = value.strip()
            
            if 'customer' in key and 'number' in key:
                reply_info['customer_number'] = value
            elif 'nick' in key:
                reply_info['nick_name'] = value
            elif 'user' in key and 'id' in key:
                reply_info['user_id'] = value
            elif 'position' in key:
                reply_info['position'] = value
            elif 'serial' in key:
                reply_info['serial'] = value
            elif 'name' in key:
                reply_info['name'] = value
    
    return reply_info

def save_database():
    """Save data to local JSON database"""
    try:
        os.makedirs("database", exist_ok=True)
        data = {
            'original_numbers': list(original_numbers),
            'reply_data': {k: v for k, v in reply_data.items()},
            'timestamp': datetime.now().isoformat()
        }
        with open('database/tracker_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        logger.info("✅ Database saved")
    except Exception as e:
        logger.error(f"❌ Database save error: {str(e)}")

def load_database():
    """Load data from local JSON database"""
    global original_numbers, reply_data
    try:
        if os.path.exists('database/tracker_data.json'):
            with open('database/tracker_data.json', 'r') as f:
                data = json.load(f)
                original_numbers = set(data.get('original_numbers', []))
                reply_data = data.get('reply_data', {})
            logger.info("✅ Database loaded")
    except Exception as e:
        logger.error(f"❌ Database load error: {str(e)}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel"""
    await update.message.reply_text("Cancelled! Use /start")
    return ConversationHandler.END

def main():
    """Start bot"""
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        print("❌ Set TELEGRAM_BOT_TOKEN environment variable")
        return
    
    load_database()
    
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
        ],
        states={
            UPLOAD_CSV: [
                MessageHandler(filters.Document.ALL, handle_csv_upload),
            ],
            REPORT_REPLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply_report),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('start', start))
    
    # Handle all callback queries
    app.add_handler(MessageHandler(
        filters.Regex('^(upload_csv|report_reply|verify|export|summary|start_bot|stop_bot)$'),
        handle_callback
    ))
    
    print("✅ Bot started. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == '__main__':
    main()
