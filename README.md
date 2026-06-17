# 🤖 Telegram Customer Response Tracker Bot

A powerful Telegram bot that helps manage and verify customer responses against an original customer number list. Perfect for tracking group member activities and ensuring data integrity.

## 📋 Features

✅ **CSV Upload** - Upload original customer number lists  
✅ **Response Tracking** - Members report customer interactions  
✅ **Duplicate Detection** - Prevents duplicate reports  
✅ **Verification System** - Check if replies match original list  
✅ **Google Drive Export** - Auto-save reports to Google Drive  
✅ **Database Storage** - Local JSON database for persistence  
✅ **Admin Controls** - Start/Stop bot, manage uploads  
✅ **Detailed Reports** - Matched, Not Matched, Missing replies  

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8+
- Telegram Bot Token (from @BotFather)
- Google Drive API credentials
- Google Drive folder for exports

### 2. Installation

```bash
# Clone repository
git clone https://github.com/JoseVenom/NumberDuplicateChecker.git
cd NumberDuplicateChecker

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

**Get Telegram Bot Token:**
1. Chat with @BotFather on Telegram
2. Send `/newbot`
3. Follow instructions and copy your token

**Setup Google Drive:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project
3. Enable Google Drive API
4. Create Service Account
5. Download JSON credentials file as `credentials.json`
6. Create folder in Google Drive
7. Share folder with service account email
8. Copy folder ID from URL: `https://drive.google.com/drive/folders/{FOLDER_ID}`

**Update bot.py:**
```python
# Line 18
ADMIN_IDS = [YOUR_TELEGRAM_USER_ID]

# Line 19
DRIVE_FOLDER_ID = "your_google_drive_folder_id"
```

Find your Telegram User ID:
- Chat with @userinfobot
- It will show your ID

### 4. Run the Bot

```bash
# Set environment variable
export TELEGRAM_BOT_TOKEN="your_bot_token_here"

# Run bot
python bot.py
```

Bot will start and show: `✅ Bot started. Press Ctrl+C to stop.`

## 📱 How to Use

### For Admins

**Start the Bot:**
```
/start
```

**Upload CSV:**
1. Click "📤 Upload CSV"
2. Send CSV file with customer numbers
3. Bot validates and saves to Google Drive

**CSV Format:**
```
Customer Number
94771234567
94771234568
94771234569
```

**Verify Replies:**
- Click "✅ Verify Replies"
- Shows matched vs not matched numbers
- Displays missing replies

**Export Reports:**
- Click "📥 Export Report"
- Creates 4 CSV files:
  - ✅ Matched_Responses.csv
  - ❌ NotMatched_Responses.csv
  - ⏳ Missing_Replies.csv
  - 📋 Summary_Report.txt
- Auto-uploads to Google Drive

**Bot Control:**
- 🤖 Start Bot - Enable bot
- ⏹️ Stop Bot - Pause bot

### For Members

**Report Responses:**
1. Click "📝 Report Reply"
2. Send customer response in format:

**Simple Format:**
```
94771234567 | John | @john_telegram | Manager | 1
```

**Or Detailed Format:**
```
Nick Name: John Doe
Customer Number: 94771234567
User ID: @john_telegram
Position: Manager
Serial: 1
Name: John Doe
```

**View Summary:**
- Click "📊 Show Summary"
- See overall statistics

## 📊 Report Structure

### Matched Numbers
Shows all customer numbers that:
- Are in the original CSV
- Have responses from members
- Includes: Name, User ID, Position, Reporter, Timestamp

### Not Matched Numbers
Shows customer numbers that:
- Are NOT in original CSV
- Have response reports
- Marked as "NOT IN ORIGINAL LIST"

### Missing Replies
Shows customer numbers that:
- Are in original CSV
- Have NO responses yet
- Need follow-up

## 💾 Database

Data is stored locally in: `database/tracker_data.json`

Contains:
- Original customer numbers
- All reply data with timestamps
- Reporter information
- Match status

Auto-saves after each action.

## 🔧 Troubleshooting

### Bot not responding
- Check TELEGRAM_BOT_TOKEN is set correctly
- Verify bot token is valid
- Check internet connection

### Google Drive upload fails
- Ensure credentials.json exists in root directory
- Verify service account has access to folder
- Check DRIVE_FOLDER_ID is correct
- Ensure Google Drive API is enabled

### CSV upload fails
- Verify CSV format (first column = Customer Number)
- Check file is not corrupted
- Try with sample data first

### Database errors
- Delete `database/tracker_data.json` to reset
- Create new `database/` folder
- Bot will recreate on next run

## 📁 Project Structure

```
NumberDuplicateChecker/
├── bot.py                 # Main bot file
├── requirements.txt       # Python dependencies
├── credentials.json       # Google Drive API (add this)
├── database/
│   └── tracker_data.json  # Local database (auto-created)
├── uploads/               # CSV uploads (auto-created)
└── README.md              # This file
```

## 🔐 Security

- Admin-only commands (upload CSV, verify, export)
- User ID verification for duplicate prevention
- Local database storage
- No cloud storage of sensitive data (only exports)

## 🐛 Known Issues

- Large CSV files (>10k numbers) may take time to upload
- Google Drive link generation requires stable internet
- Duplicate reports tracked per user per number

## 📈 Future Enhancements

- [ ] Database migration to cloud (MongoDB/Firebase)
- [ ] Webhook support for faster responses
- [ ] Multi-language support
- [ ] Analytics dashboard
- [ ] Bulk import/export
- [ ] API endpoints

## 📞 Support

For issues, questions, or suggestions:
1. Check troubleshooting section
2. Review bot logs
3. Create GitHub issue

## 📄 License

MIT License - Feel free to use and modify

## 👨‍💻 Author

JoseVenom - [GitHub Profile](https://github.com/JoseVenom)

---

**Happy Tracking! 🚀**
