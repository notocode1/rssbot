import time
import telebot
from config import BOT_TOKEN  # Make sure this import is here
from db import init_db, save_group, get_last_seen_time
from commands import register_commands
from feeds import start_feed_loop
import config  # Add this line to import the config

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='MarkdownV2')

@bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'])
def on_group_message(msg):
    save_group(msg.chat.id, msg.chat.title, msg.chat.type)

def run_bot(config):
    init_db()
    start_time = get_last_seen_time() or time.time()
    register_commands(bot)
    start_feed_loop(bot, start_time)
    print("🚀 Bot is running")
    bot.infinity_polling()

@bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'])
def on_group_message(msg):
    # Save the group to the database
    save_group(msg.chat.id, msg.chat.title, msg.chat.type)
    
    # Send a confirmation message to the owner (you)
    added_message = (
        f"🆕 New Group Added:\n\n"
        f"*Title:* {escape_markdown(msg.chat.title, version=2)}\n"
        f"*Chat ID:* `{msg.chat.id}`\n"
        f"*Type:* `{msg.chat.type}`"
    )
    bot.send_message(OWNER_ID, added_message, parse_mode='MarkdownV2')
    
    # Optionally, send a welcome message to the new group
    welcome_message = (
        f"Hey! Thanks for adding me to this group. "
        f"I'll keep you updated with the latest feeds!"
    )
    bot.send_message(msg.chat.id, welcome_message)

# Ensure that the bot runs when this file is executed directly
if __name__ == "__main__":
    run_bot(config)  # This passes the imported config to the function
