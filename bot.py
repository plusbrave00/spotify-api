#!/usr/bin/env python3
"""
YuviMods ADB Remote Controller Bot
Multi-user Telegram bot for Android device management
Made by @YuviModsOwner
"""

import os
import sqlite3
import subprocess
import tempfile
import uuid
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

# ==================== CONFIG ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8732813107:AAHwesfbzAx4IQdugicmoJWtTTQk0u7SS38")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8583790625"))
DB_NAME = "adb_premium.db"
BRANDING = "\n\n🍁 *This bot is made by @YuviModsOwner* 🍁"
TIMEOUT = 15
MAX_RESPONSE = 4000

# ==================== KEYBOARDS ====================
USER_KEYBOARD = [
    ["📱 Status & Device", "🔌 Connect to Device"],
    ["📸 Screen Snapshot", "🔋 Battery Status"],
    ["📩 Request Verification", "ℹ️ Help Info"],
]

ADMIN_KEYBOARD = [
    ["📱 Status & Device", "🔌 Connect to Device"],
    ["📸 Screen Snapshot", "🔋 Battery Status"],
    ["📩 Request Verification", "ℹ️ Help Info"],
    ["👑 Admin Control Panel"],
]

ADMIN_PANEL_KEYBOARD = [
    ["👥 Registered Users", "⏳ Pending Requests"],
    ["🔑 Generate Promo Code", "🔌 Check ADB Services"],
    ["🔙 Return to User Menu"],
]

user_reply_keyboard = ReplyKeyboardMarkup(USER_KEYBOARD, resize_keyboard=True)
admin_reply_keyboard = ReplyKeyboardMarkup(ADMIN_KEYBOARD, resize_keyboard=True)
admin_panel_keyboard = ReplyKeyboardMarkup(ADMIN_PANEL_KEYBOARD, resize_keyboard=True)


# ==================== DATABASE ====================
def init_db():
    """Initialize SQLite database with required tables."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            expiry_date TEXT,
            device_ip TEXT,
            status TEXT DEFAULT 'active'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS verification_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            details TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS promo_keys (
            key TEXT PRIMARY KEY,
            duration_days INTEGER,
            is_used INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def get_user(user_id):
    """Get user from database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user


def add_user(user_id, username, expiry_date=None):
    """Add new user to database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if expiry_date is None:
        expiry_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT OR REPLACE INTO users (user_id, username, expiry_date, status) VALUES (?, ?, ?, 'active')",
        (user_id, username, expiry_date),
    )
    conn.commit()
    conn.close()


def update_device_ip(user_id, device_ip):
    """Update user's device IP."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET device_ip = ? WHERE user_id = ?", (device_ip, user_id))
    conn.commit()
    conn.close()


def get_device_ip(user_id):
    """Get user's device IP."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT device_ip FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result and result[0] else None


def is_subscribed(user_id):
    """Check if user subscription is active."""
    user = get_user(user_id)
    if not user:
        return False
    try:
        expiry = datetime.strptime(user[2], "%Y-%m-%d %H:%M:%S")
        return datetime.now() < expiry and user[4] == 'active'
    except Exception:
        return False


def add_verification_request(user_id, username, details):
    """Add verification request."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO verification_requests (user_id, username, details) VALUES (?, ?, ?)",
        (user_id, username, details),
    )
    conn.commit()
    conn.close()


def get_pending_requests():
    """Get all pending verification requests."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM verification_requests WHERE status = 'pending'")
    requests = c.fetchall()
    conn.close()
    return requests


def approve_request(request_id):
    """Approve a verification request."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, username FROM verification_requests WHERE request_id = ?", (request_id,))
    result = c.fetchone()
    if result:
        user_id, username = result
        expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT OR REPLACE INTO users (user_id, username, expiry_date, status) VALUES (?, ?, ?, 'active')",
                  (user_id, username, expiry))
        c.execute("UPDATE verification_requests SET status = 'approved' WHERE request_id = ?", (request_id,))
        conn.commit()
        conn.close()
        return user_id, expiry
    conn.close()
    return None, None


def reject_request(request_id):
    """Reject a verification request."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM verification_requests WHERE request_id = ?", (request_id,))
    result = c.fetchone()
    if result:
        c.execute("UPDATE verification_requests SET status = 'rejected' WHERE request_id = ?", (request_id,))
        conn.commit()
        conn.close()
        return result[0]
    conn.close()
    return None


def get_all_users():
    """Get all registered users."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return users


def create_promo_key(days):
    """Create a promo key."""
    key = f"KEY-{days}D-{uuid.uuid4().hex[:8].upper()}"
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO promo_keys (key, duration_days) VALUES (?, ?)", (key, days))
    conn.commit()
    conn.close()
    return key


def redeem_promo_key(key):
    """Redeem a promo key."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT duration_days FROM promo_keys WHERE key = ? AND is_used = 0", (key,))
    result = c.fetchone()
    if result:
        c.execute("UPDATE promo_keys SET is_used = 1 WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        return result[0]
    conn.close()
    return None


# ==================== ADB HELPERS ====================
async def adb_connect(device_ip):
    """Connect to device via ADB."""
    try:
        proc = await asyncio.create_subprocess_shell(
            f"adb connect {device_ip}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        output = stdout.decode("utf-8", errors="replace")
        return output
    except Exception as e:
        return f"Error: {str(e)}"


async def run_adb_command(command):
    """Run an ADB command with timeout."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT)
        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")
        return output if output else error
    except asyncio.TimeoutError:
        return "⏰ Command timed out (15s limit)"
    except Exception as e:
        return f"❌ Error: {str(e)}"


async def execute_adb_for_user(user_id, adb_args):
    """Execute ADB command for specific user with auto-connect."""
    device_ip = get_device_ip(user_id)
    if not device_ip:
        return "❌ No device connected. Use /setdevice <IP:PORT> first."

    # First connect to device
    connect_result = await adb_connect(device_ip)
    
    # Run the command
    full_cmd = f"adb -s {device_ip} {adb_args}"
    result = await run_adb_command(full_cmd)
    
    return result


# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    user_id = user.id
    username = user.first_name

    db_user = get_user(user_id)
    if not db_user:
        add_user(user_id, username)

    keyboard = admin_reply_keyboard if user_id == ADMIN_ID else user_reply_keyboard

    welcome_msg = (
        f"👋 Welcome *{username}*!\n\n"
        f"🍁 *YuviMods ADB Remote Controller* 🍁\n\n"
        f"📱 Connect and control your Android device remotely.\n"
        f"🔐 Subscription required for full access.\n\n"
        f"Use the buttons below to navigate.{BRANDING}"
    )

    await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help button."""
    help_text = (
        f"📖 *YuviMods ADB Bot - Help Guide*\n\n"
        f"📱 *Status & Device* - Check connected device\n"
        f"🔌 *Connect to Device* - Set device IP:PORT\n"
        f"📸 *Screen Snapshot* - Take device screenshot\n"
        f"🔋 *Battery Status* - Check battery info\n"
        f"📩 *Request Verification* - Request access\n\n"
        f"💡 *Commands:*\n"
        f"/setdevice <IP:PORT> - Set device\n"
        f"/shell <command> - Run ADB command\n"
        f"/redeem <key> - Redeem promo key\n"
        f"/request <details> - Request access\n\n"
        f"👑 *Admin Only:*\n"
        f"/genkey <days> - Generate promo key{BRANDING}"
    )

    keyboard = admin_reply_keyboard if update.effective_user.id == ADMIN_ID else user_reply_keyboard
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def status_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Status & Device button."""
    user_id = update.effective_user.id

    if not is_subscribed(user_id):
        await update.message.reply_text(
            f"🔐 *Subscription Required*\n\n"
            f"You need an active subscription to use this feature.\n\n"
            f"💡 Use /request <txn_id> to request access.\n"
            f"Or use /redeem <key> if you have a promo key.{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    device_ip = get_device_ip(user_id)
    if not device_ip:
        await update.message.reply_text(
            f"⚠️ *No Device Connected*\n\n"
            f"Use /setdevice <IP:PORT> to connect your device.\n"
            f"Or press 🔌 *Connect to Device* button.{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Try to connect and get device info
    connect_result = await adb_connect(device_ip)
    result = await execute_adb_for_user(user_id, "get-state")
    
    user = get_user(user_id)
    expiry = user[2] if user else "Unknown"

    device_state = "🟢 Connected" if "device" in result.lower() else "🔴 Disconnected"

    status_text = (
        f"📱 *Device Status*\n\n"
        f"🔗 *Device:* `{device_ip}`\n"
        f"👤 *User:* {update.effective_user.first_name}\n"
        f"📅 *Expiry:* {expiry}\n"
        f"📡 *State:* {device_state}\n\n"
        f"💡 Use /shell <command> to run commands.{BRANDING}"
    )

    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)


async def connect_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Connect to Device button."""
    user_id = update.effective_user.id

    if not is_subscribed(user_id):
        await update.message.reply_text(
            f"🔐 *Subscription Required*\n\n"
            f"You need an active subscription to connect devices.{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await update.message.reply_text(
        f"🔌 *Connect to Device*\n\n"
        f"Send your device IP and port in this format:\n"
        f"`192.168.1.100:5555`\n\n"
        f"💡 Or use command: /setdevice <IP:PORT>{BRANDING}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def screen_snapshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Screen Snapshot button."""
    user_id = update.effective_user.id

    if not is_subscribed(user_id):
        await update.message.reply_text(
            f"🔐 *Subscription Required*{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    device_ip = get_device_ip(user_id)
    if not device_ip:
        await update.message.reply_text(
            f"⚠️ *No Device Connected*\n\n"
            f"Use /setdevice <IP:PORT> first.{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
    wait_msg = await update.message.reply_text("📸 Taking screenshot...")

    # Connect first
    await adb_connect(device_ip)

    # Take screenshot on device
    result = await run_adb_command(f"adb -s {device_ip} shell screencap -p /sdcard/screenshot.png")

    if "error" in result.lower() or "timed out" in result.lower():
        await wait_msg.edit_text(f"❌ Screenshot failed: {result}{BRANDING}")
        return

    # Pull screenshot to local
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, "screenshot.png")

    try:
        pull_result = await run_adb_command(f"adb -s {device_ip} pull /sdcard/screenshot.png {temp_file}")

        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
            with open(temp_file, "rb") as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"📸 Device Screenshot\n🔗 {device_ip}{BRANDING}",
                )
            await wait_msg.delete()
        else:
            await wait_msg.edit_text(f"❌ Failed to capture screenshot{BRANDING}")
    except Exception as e:
        await wait_msg.edit_text(f"❌ Error: {str(e)}{BRANDING}")
    finally:
        # Cleanup local files
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        # Cleanup on device
        await run_adb_command(f"adb -s {device_ip} shell rm /sdcard/screenshot.png")


async def battery_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Battery Status button."""
    user_id = update.effective_user.id

    if not is_subscribed(user_id):
        await update.message.reply_text(
            f"🔐 *Subscription Required*{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    device_ip = get_device_ip(user_id)
    if not device_ip:
        await update.message.reply_text(
            f"⚠️ *No Device Connected*\n\n"
            f"Use /setdevice <IP:PORT> first.{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    wait_msg = await update.message.reply_text("🔋 Checking battery status...")

    # Connect first
    await adb_connect(device_ip)

    result = await run_adb_command(f"adb -s {device_ip} shell dumpsys battery")

    if "error" in result.lower() or "timed out" in result.lower():
        await wait_msg.edit_text(f"❌ Battery check failed: {result}{BRANDING}")
        return

    battery_info = ""
    for line in result.split("\n"):
        line = line.strip()
        if any(key in line.lower() for key in ["level", "temperature", "voltage", "status", "health"]):
            battery_info += f"• {line}\n"

    if battery_info:
        msg = f"🔋 *Battery Status*\n\n{battery_info}{BRANDING}"
    else:
        msg = f"🔋 *Battery Status*\n\n```\n{result[:2000]}\n```{BRANDING}"

    await wait_msg.edit_text(msg, parse_mode=ParseMode.MARKDOWN)


async def request_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Request Verification button."""
    await update.message.reply_text(
        f"📩 *Request Verification*\n\n"
        f"Send your payment transaction ID or details:\n"
        f"/request <txn_id or details>\n\n"
        f"Example: /request UPI-123456789{BRANDING}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ==================== COMMAND HANDLERS ====================
async def setdevice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setdevice command."""
    user_id = update.effective_user.id

    if not is_subscribed(user_id):
        await update.message.reply_text(
            f"🔐 *Subscription Required*{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not context.args:
        await update.message.reply_text(
            f"⚠️ *Usage:* /setdevice <IP:PORT>\n\n"
            f"Example: /setdevice 192.168.1.100:5555\n\n"
            f"💡 Make sure ADB is enabled on your device.\n"
            f"Settings > Developer Options > Wireless Debugging{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    device_ip = context.args[0]
    
    # Test connection
    wait_msg = await update.message.reply_text(f"🔌 Connecting to {device_ip}...")
    
    connect_result = await adb_connect(device_ip)
    
    if "connected" in connect_result.lower():
        update_device_ip(user_id, device_ip)
        await wait_msg.edit_text(
            f"✅ *Device Connected!*\n\n"
            f"🔗 *Device:* `{device_ip}`\n"
            f"📡 *Result:* {connect_result}\n\n"
            f"💡 Use /shell <command> to run ADB commands.{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await wait_msg.edit_text(
            f"❌ *Connection Failed!*\n\n"
            f"🔗 *Device:* `{device_ip}`\n"
            f"📡 *Result:* {connect_result}\n\n"
            f"💡 Make sure:\n"
            f"1. Device is on same WiFi\n"
            f"2. ADB debugging is enabled\n"
            f"3. IP and port are correct\n"
            f"4. Try: Settings > Developer Options > Wireless Debugging{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )


async def shell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shell command."""
    user_id = update.effective_user.id

    if not is_subscribed(user_id):
        await update.message.reply_text(
            f"🔐 *Subscription Required*{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    device_ip = get_device_ip(user_id)
    if not device_ip:
        await update.message.reply_text(
            f"⚠️ *No Device Connected*\n\n"
            f"Use /setdevice <IP:PORT> first.{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not context.args:
        await update.message.reply_text(
            f"⚠️ *Usage:* /shell <command>\n\n"
            f"Examples:\n"
            f"/shell pm list packages\n"
            f"/shell getprop ro.build.version.release\n"
            f"/shell ls /sdcard/{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    command = " ".join(context.args)
    wait_msg = await update.message.reply_text(f"⏳ Running: `{command}`", parse_mode=ParseMode.MARKDOWN)

    result = await execute_adb_for_user(user_id, f"shell {command}")

    if len(result) > MAX_RESPONSE:
        result = result[:MAX_RESPONSE] + "\n\n... (truncated)"

    if not result.strip():
        result = "(no output)"

    await wait_msg.edit_text(
        f"📱 *Shell Output:*\n\n```\n{result}\n```{BRANDING}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def request_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /request command."""
    user_id = update.effective_user.id
    username = update.effective_user.first_name

    if not context.args:
        await update.message.reply_text(
            f"⚠️ *Usage:* /request <txn_id or details>\n\n"
            f"Example: /request UPI-123456789{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    details = " ".join(context.args)
    add_verification_request(user_id, username, details)

    admin_msg = (
        f"📩 *New Verification Request*\n\n"
        f"👤 *User:* {username}\n"
        f"🆔 *ID:* `{user_id}`\n"
        f"📝 *Details:* {details}\n\n"
        f"Use Admin Panel to approve/reject.{BRANDING}"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        pass

    await update.message.reply_text(
        f"✅ *Request Submitted!*\n\n"
        f"Your request has been sent to the admin.\n"
        f"You will be notified once approved.{BRANDING}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /redeem command."""
    user_id = update.effective_user.id
    username = update.effective_user.first_name

    if not context.args:
        await update.message.reply_text(
            f"⚠️ *Usage:* /redeem <key>\n\n"
            f"Example: /redeem KEY-30D-ABC12345{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    key = context.args[0]
    days = redeem_promo_key(key)

    if days:
        user = get_user(user_id)
        if user and user[2]:
            try:
                current_expiry = datetime.strptime(user[2], "%Y-%m-%d %H:%M:%S")
                if current_expiry > datetime.now():
                    new_expiry = current_expiry + timedelta(days=days)
                else:
                    new_expiry = datetime.now() + timedelta(days=days)
            except Exception:
                new_expiry = datetime.now() + timedelta(days=days)
        else:
            new_expiry = datetime.now() + timedelta(days=days)

        expiry_str = new_expiry.strftime("%Y-%m-%d %H:%M:%S")
        add_user(user_id, username, expiry_str)

        await update.message.reply_text(
            f"🎉 *Key Redeemed Successfully!*\n\n"
            f"🔑 *Key:* `{key}`\n"
            f"📅 *Duration:* {days} days\n"
            f"⏰ *New Expiry:* {expiry_str}\n\n"
            f"✅ You now have full access!{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text(
            f"❌ *Invalid or Used Key*\n\n"
            f"The key `{key}` is invalid or already redeemed.{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )


# ==================== ADMIN HANDLERS ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Admin Control Panel button."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied.")
        return

    await update.message.reply_text(
        f"👑 *Admin Control Panel*\n\n"
        f"Select an option from the keyboard below.{BRANDING}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard,
    )


async def registered_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Registered Users button."""
    if update.effective_user.id != ADMIN_ID:
        return

    users = get_all_users()
    if not users:
        await update.message.reply_text(f"👥 No registered users yet.{BRANDING}")
        return

    msg = f"👥 *Registered Users ({len(users)})*\n\n"
    for u in users:
        status = "✅" if u[4] == 'active' else "❌"
        msg += f"{status} *{u[1]}* (`{u[0]}`)\n📅 Expiry: {u[2]}\n🔗 Device: {u[3] or 'Not set'}\n\n"

    if len(msg) > MAX_RESPONSE:
        msg = msg[:MAX_RESPONSE] + "\n\n... (truncated)"

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def pending_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Pending Requests button."""
    if update.effective_user.id != ADMIN_ID:
        return

    requests = get_pending_requests()
    if not requests:
        await update.message.reply_text(f"⏳ No pending requests.{BRANDING}")
        return

    for req in requests:
        req_id, user_id, username, details, status = req

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Approve ✅ (30 Days)", callback_data=f"approve_{req_id}"),
                InlineKeyboardButton("Reject ❌", callback_data=f"reject_{req_id}"),
            ]
        ])

        msg = (
            f"📩 *Request #{req_id}*\n\n"
            f"👤 *User:* {username}\n"
            f"🆔 *ID:* `{user_id}`\n"
            f"📝 *Details:* {details}\n"
            f"⏳ *Status:* {status}"
        )

        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def check_adb_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Check ADB Services button."""
    if update.effective_user.id != ADMIN_ID:
        return

    wait_msg = await update.message.reply_text("🔌 Checking ADB services...")
    
    result = await run_adb_command("adb start-server")
    devices = await run_adb_command("adb devices")

    msg = (
        f"🔌 *ADB Services Status*\n\n"
        f"```\n{devices}\n```{BRANDING}"
    )

    await wait_msg.edit_text(msg, parse_mode=ParseMode.MARKDOWN)


async def return_to_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Return to User Menu button."""
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        f"🔙 Back to User Menu{BRANDING}",
        reply_markup=admin_reply_keyboard,
    )


async def genkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /genkey command for admin."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied.")
        return

    if not context.args:
        await update.message.reply_text(
            f"⚠️ *Usage:* /genkey <days>\n\n"
            f"Example: /genkey 30{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        days = int(context.args[0])
    except ValueError:
        await update.message.reply_text(f"❌ Invalid number of days.{BRANDING}")
        return

    key = create_promo_key(days)

    await update.message.reply_text(
        f"🔑 *Promo Key Generated!*\n\n"
        f"📅 *Duration:* {days} days\n"
        f"🔑 *Key:* `{key}`\n\n"
        f"Share this key with users.{BRANDING}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ==================== CALLBACK HANDLER ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Access Denied.")
        return

    data = query.data

    if data.startswith("approve_"):
        req_id = int(data.split("_")[1])
        user_id, expiry = approve_request(req_id)

        if user_id:
            await query.edit_message_text(
                f"✅ *Request #{req_id} Approved!*\n\n"
                f"📅 Access granted until: {expiry}{BRANDING}",
                parse_mode=ParseMode.MARKDOWN,
            )

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🎉 *Congratulations!*\n\n"
                        f"Your request has been *approved*!\n"
                        f"📅 *Access until:* {expiry}\n\n"
                        f"✅ You now have full access to all features.\n"
                        f"Use /start to begin.{BRANDING}"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
        else:
            await query.edit_message_text(f"❌ Request not found.{BRANDING}")

    elif data.startswith("reject_"):
        req_id = int(data.split("_")[1])
        user_id = reject_request(req_id)

        if user_id:
            await query.edit_message_text(
                f"❌ *Request #{req_id} Rejected*{BRANDING}",
                parse_mode=ParseMode.MARKDOWN,
            )

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"❌ *Request Denied*\n\n"
                        f"Your verification request has been denied.\n"
                        f"Please contact admin for more info.{BRANDING}"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
        else:
            await query.edit_message_text(f"❌ Request not found.{BRANDING}")


# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages based on button clicks."""
    text = update.message.text
    user_id = update.effective_user.id

    if text == "📱 Status & Device":
        await status_device(update, context)
    elif text == "🔌 Connect to Device":
        await connect_device(update, context)
    elif text == "📸 Screen Snapshot":
        await screen_snapshot(update, context)
    elif text == "🔋 Battery Status":
        await battery_status(update, context)
    elif text == "📩 Request Verification":
        await request_verification(update, context)
    elif text == "ℹ️ Help Info":
        await help_command(update, context)
    elif text == "👑 Admin Control Panel":
        await admin_panel(update, context)
    elif text == "👥 Registered Users":
        await registered_users(update, context)
    elif text == "⏳ Pending Requests":
        await pending_requests(update, context)
    elif text == "🔑 Generate Promo Code":
        await update.message.reply_text(
            f"🔑 *Generate Promo Code*\n\n"
            f"Use /genkey <days> command.\n"
            f"Example: /genkey 30{BRANDING}",
            parse_mode=ParseMode.MARKDOWN,
        )
    elif text == "🔌 Check ADB Services":
        await check_adb_services(update, context)
    elif text == "🔙 Return to User Menu":
        await return_to_user_menu(update, context)
    elif ":" in text and is_subscribed(user_id):
        # User might be setting device IP
        device_ip = text.strip()
        wait_msg = await update.message.reply_text(f"🔌 Connecting to {device_ip}...")
        
        connect_result = await adb_connect(device_ip)
        
        if "connected" in connect_result.lower():
            update_device_ip(user_id, device_ip)
            await wait_msg.edit_text(
                f"✅ *Device Connected!*\n\n"
                f"🔗 *Device:* `{device_ip}`\n"
                f"📡 *Result:* {connect_result}{BRANDING}",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await wait_msg.edit_text(
                f"❌ *Connection Failed!*\n\n"
                f"🔗 *Device:* `{device_ip}`\n"
                f"📡 *Result:* {connect_result}\n\n"
                f"💡 Make sure ADB is enabled on your device.{BRANDING}",
                parse_mode=ParseMode.MARKDOWN,
            )


# ==================== ERROR HANDLER ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    print(f"Error: {context.error}")
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"⚠️ An error occurred. Please try again.{BRANDING}"
            )
        except Exception:
            pass


# ==================== MAIN ====================
def main():
    """Start the bot."""
    print("Starting YuviMods ADB Bot...")
    init_db()
    print("Database initialized.")

    # Start ADB server
    os.system("adb start-server")
    print("ADB server started.")

    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("setdevice", setdevice_command))
    app.add_handler(CommandHandler("shell", shell_command))
    app.add_handler(CommandHandler("request", request_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(CommandHandler("genkey", genkey_command))

    # Callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(button_callback))

    # Message handler for keyboard buttons
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Error handler
    app.add_error_handler(error_handler)

    print("Bot is running... 🍁 This bot is made by @YuviModsOwner 🍁")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
