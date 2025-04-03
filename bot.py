import time
import telebot
from config import BOT_TOKEN, OWNER_ID
from db import init_db, save_group, get_last_seen_time, is_group_saved
from feeds import start_feed_loop
from commands import register_commands
import config
import db  # needed for command registration
from utils import escape_markdown

print("⚙️ bot.py is starting...")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='MarkdownV2')

@bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'])
def on_group_message(msg):
    try:
        if not is_group_saved(msg.chat.id):
            save_group(msg.chat.id, msg.chat.title, msg.chat.type)
            added_message = (
                f"🆕 New Group Added:\n\n"
                f"*Title:* {escape_markdown(msg.chat.title, version=2)}\n"
                f"*Chat ID:* `{msg.chat.id}`\n"
                f"*Type:* `{msg.chat.type}`"
            )
            bot.send_message(OWNER_ID, added_message, parse_mode='MarkdownV2')
    except Exception as e:
        print(f"❌ Error saving group: {e}")

def run_bot():
    try:
        init_db()
        register_commands(bot, db)
        start_time = get_last_seen_time() or time.time()
        print("✅ Commands registered. Starting feed loop...")
        start_feed_loop(bot, start_time)
        print("🚀 Bot is running")
        bot.infinity_polling()
    except Exception as e:
        print(f"🔥 Bot failed to start: {e}")

if __name__ == "__main__":
    run_bot()
