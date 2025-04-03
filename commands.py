from config import OWNER_ID
from telebot import TeleBot
from db import add_feed, remove_feed, get_feeds, get_groups
from utils import escape_markdown

def register_commands(bot: TeleBot, db):
    # Handle /add command - Only for the owner in private messages
    @bot.message_handler(commands=['add'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def add_feed_cmd(msg):
        print(f"Received /add command: {msg.text}")
        parts = msg.text.split(" ", 1)
        if len(parts) < 2:
            bot.reply_to(msg, escape_markdown("Usage: /add <rss_url>", version=2))
            return
        
        feed_url = parts[1].strip()
        try:
            add_feed(feed_url, db)  # Pass db to add_feed
            bot.send_message(OWNER_ID, f"✅ A new feed has been successfully added: {feed_url}")
            bot.reply_to(msg, escape_markdown("✅ Feed added successfully.", version=2))
        except Exception as e:
            bot.send_message(OWNER_ID, f"❌ Failed to add feed: {feed_url}. Error: {str(e)}")
            bot.reply_to(msg, escape_markdown(f"❌ Feed could not be added. Error: {str(e)}", version=2))

    # Handle /remove command - Only for the owner in private messages
    @bot.message_handler(commands=['remove'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def remove_feed_cmd(msg):
        print(f"Received /remove command: {msg.text}")
        parts = msg.text.split(" ", 1)
        if len(parts) < 2:
            bot.reply_to(msg, escape_markdown("Usage: /remove <rss_url>", version=2))
            return
        feed_url = parts[1].strip()
        try:
            remove_feed(feed_url, db)  # Pass db
            bot.send_message(OWNER_ID, f"✅ Feed has been successfully removed: {feed_url}")
            bot.reply_to(msg, escape_markdown("🗑️ Feed removed successfully.", version=2))
        except Exception as e:
            bot.send_message(OWNER_ID, f"❌ Failed to remove feed: {feed_url}. Error: {str(e)}")
            bot.reply_to(msg, escape_markdown(f"❌ Feed could not be removed. Error: {str(e)}", version=2))

    # Handle /feeds command - Only for the owner in private messages
    @bot.message_handler(commands=['feeds'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def list_feeds_cmd(msg):
        print(f"Received /feeds command: {msg.text}")
        feeds = get_feeds(db)  # Pass db
        if not feeds:
            bot.reply_to(msg, escape_markdown("No feeds found.", version=2))
        else:
            feed_list = "\n".join([escape_markdown(url, version=2) for url in feeds])
            bot.send_message(msg.chat.id, feed_list, disable_web_page_preview=True)

    # Handle /alive command - Only for the owner in private messages
    @bot.message_handler(commands=['alive'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def alive_cmd(msg):
        print(f"Received /alive command: {msg.text}")
        bot.reply_to(msg, escape_markdown("I'm alive and running!", version=2))
