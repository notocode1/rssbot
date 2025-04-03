from config import OWNER_ID
from telebot import TeleBot
from db import add_feed, remove_feed, get_feeds, get_groups
from utils import escape_markdown

def register_commands(bot: TeleBot, db):  # Add db parameter
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
        bot.send_message(msg.chat.id, escape_markdown("✅ Bot is alive.", version=2))

    # Handle /stats command - Only for the owner in private messages
    @bot.message_handler(commands=['stats'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def stats_cmd(msg):
        print(f"Received /stats command: {msg.text}")
        groups = len(get_groups(db))  # Pass db
        feeds = len(get_feeds(db))   # Pass db
        stats_text = (
            f"📊 *Bot Stats*\n\n"
            f"👥 Groups: *{groups}*\n"
            f"📡 Feeds: *{feeds}*"
        )
        bot.send_message(msg.chat.id, stats_text, parse_mode='MarkdownV2')

    # Handle /broadcast command - Only for the owner in private messages
    @bot.message_handler(commands=['broadcast'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def broadcast_cmd(msg):
        print(f"Received /broadcast command: {msg.text}")
        parts = msg.text.split(" ", 1)
        if len(parts) < 2:
            bot.reply_to(msg, escape_markdown("Usage: /broadcast <message>", version=2))
            return
        broadcast_message = parts[1].strip()
        groups = get_groups(db)  # Pass db
        for chat_id in groups:
            try:
                bot.send_message(chat_id, broadcast_message, disable_web_page_preview=False)
            except Exception as e:
                print(f"Error broadcasting to chat {chat_id}: {e}")
        bot.reply_to(msg, escape_markdown(f"✅ Broadcast message sent to {len(groups)} groups.", version=2))
