from config import OWNER_ID
from telebot import TeleBot
from db import add_feed, remove_feed, get_feeds
from utils import escape_markdown

def register_commands(bot: TeleBot):

    @bot.message_handler(commands=['alive'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def alive_cmd(msg):
        print("✅ /alive command triggered")
        bot.reply_to(msg, escape_markdown("I'm alive and running!", version=2))

    @bot.message_handler(commands=['add'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def add_feed_cmd(msg):
        print(f"📥 /add command: {msg.text}")
        parts = msg.text.split(" ", 1)
        if len(parts) < 2:
            bot.reply_to(msg, escape_markdown("Usage: /add <rss_url>", version=2))
            return
        feed_url = parts[1].strip()
        try:
            add_feed(feed_url)
            bot.send_message(OWNER_ID, f"✅ Feed added: {feed_url}")
        except Exception as e:
            bot.send_message(OWNER_ID, f"❌ Error adding feed: {e}")

    @bot.message_handler(commands=['remove'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def remove_feed_cmd(msg):
        print(f"🗑️ /remove command: {msg.text}")
        parts = msg.text.split(" ", 1)
        if len(parts) < 2:
            bot.reply_to(msg, escape_markdown("Usage: /remove <rss_url>", version=2))
            return
        feed_url = parts[1].strip()
        try:
            remove_feed(feed_url)
            bot.send_message(OWNER_ID, f"✅ Feed removed: {feed_url}")
        except Exception as e:
            bot.send_message(OWNER_ID, f"❌ Error removing feed: {e}")

    @bot.message_handler(commands=['feeds'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def list_feeds_cmd(msg):
        print("📋 /feeds command triggered")
        feeds = get_feeds()
        if not feeds:
            bot.reply_to(msg, escape_markdown("No feeds found.", version=2))
        else:
            feed_list = "\n".join([escape_markdown(url, version=2) for url in feeds])
            bot.send_message(msg.chat.id, feed_list, disable_web_page_preview=True)
