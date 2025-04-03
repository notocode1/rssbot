import time
import telebot
from config import BOT_TOKEN, OWNER_ID
from db import init_db, save_group, get_last_seen_time, is_group_saved
from feeds import start_feed_loop
import config
from utils import escape_markdown

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='MarkdownV2')

@bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'])
def on_group_message(msg):
    try:
        # Check if the group is already in the database
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
        print(f"Error processing group message: {e}")  # Print error if something goes wrong

def run_bot():
    try:
        init_db()  # Initialize the database
        start_time = get_last_seen_time() or time.time()
        start_feed_loop(bot, start_time)  # Start processing feeds
        print("🚀 Bot is running")
        bot.infinity_polling()  # Start polling for updates
    except Exception as e:
        print(f"Error running bot: {e}")  # Print error if something goes wrong during the bot startup

# Ensure that the bot runs when this file is executed directly
if __name__ == "__main__":
    run_bot()
