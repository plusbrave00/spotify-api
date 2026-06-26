# YuviMods ADB Remote Controller Bot
# Made by @YuviModsOwner

## Files:
1. bot.py - Main bot code
2. requirements.txt - Python dependencies
3. Dockerfile - For Railway.app deployment

## Setup Steps:

### 1. Create Telegram Bot
- Open Telegram, search @BotFather
- Send /newbot
- Choose name and username
- Copy the bot token

### 2. Get Your User ID
- Search @userinfobot on Telegram
- Send /start
- Copy your user ID (this is ADMIN_ID)

### 3. Deploy on Railway.app
1. Create account at railway.app
2. Create new project
3. Connect your GitHub repo (upload these files)
4. Add environment variables:
   - BOT_TOKEN = your bot token
   - ADMIN_ID = your user ID
5. Deploy

### 4. Deploy on Render.com (Alternative)
1. Create account at render.com
2. Create new Web Service
3. Connect GitHub repo
4. Select Docker as runtime
5. Add environment variables
6. Deploy

## Bot Features:

### User Keyboard:
📱 Status & Device - Check connected device
🔌 Connect to Device - Set device IP:PORT
📸 Screen Snapshot - Take device screenshot
🔋 Battery Status - Check battery info
📩 Request Verification - Request access
ℹ️ Help Info - Help guide

### Admin Keyboard:
👑 Admin Control Panel - Admin menu
👥 Registered Users - List all users
⏳ Pending Requests - View pending requests
🔑 Generate Promo Code - Create promo key
🔌 Check ADB Services - Check ADB status
🔙 Return to User Menu - Back to user menu

### Commands:
/start - Start bot
/help - Help guide
/setdevice <IP:PORT> - Set device
/shell <command> - Run ADB command
/request <details> - Request access
/redeem <key> - Redeem promo key
/genkey <days> - Generate promo key (Admin)

## Branding:
Every response ends with:
🍁 This bot is made by @YuviModsOwner 🍁

## Database:
- SQLite database (adb_premium.db)
- Auto-created on first run
- Stores users, requests, promo keys

## Notes:
- Device must have ADB over network enabled
- Use port 5555 for ADB connection
- Multiple users can connect different devices
- Each user's commands only affect their device
