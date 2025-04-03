import time
import telebot
from config import BOT_TOKEN, OWNER_ID  # Import the bot token and OWNER_ID
from db import init_db, save_group, get_last_seen_time
from feeds import start_feed_loop
import config
from utils import escape_markdown

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='MarkdownV2')

# Only process group messages to add the group to the database
@bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'])
def on_group_message(msg):
    # Save the group to the database (no need to check sender, just process the message)
    save_group(msg.chat.id, msg.chat.title, msg.chat.type)
    
    # Send a confirmation message to the owner (you) privately
    added_message = (
        f"🆕 New Group Added:\n\n"
        f"*Title:* {escape_markdown(msg.chat.title, version=2)}\n"
        f"*Chat ID:* `{msg.chat.id}`\n"
        f"*Type:* `{msg.chat.type}`"
    )
    bot.send_message(OWNER_ID, added_message, parse_mode='MarkdownV2')
    
def run_bot():
    init_db()  # Initialize the database
    start_time = get_last_seen_time() or time.time()
    start_feed_loop(bot, start_time)  # Start processing feeds
    print("🚀 Bot is running")
    bot.infinity_polling()  # Start polling for updates

# Ensure that the bot runs when this file is executed directly
if __name__ == "__main__":
    run_bot()
