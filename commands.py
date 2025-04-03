from config import OWNER_ID
from telebot import TeleBot
from db import add_feed, remove_feed, get_feeds
from utils import escape_markdown

def register_commands(bot: TeleBot):

    @bot.message_handler(commands=['alive'])
    def alive_cmd(msg):
        print(f"⚡ /alive hit by user: {msg.from_user.id} | chat_type: {msg.chat.type}")
        if msg.from_user.id == OWNER_ID and msg.chat.type == 'private':
            bot.reply_to(msg, escape_markdown("✅ I am alive and you are the boss", version=2))
        else:
            bot.reply_to(msg, escape_markdown("❌ You are not the owner", version=2))

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
            bot.send_message(OWNER_ID, escape_markdown(f"✅ Feed added: {feed_url}", version=2))
        except Exception as e:
            bot.send_message(OWNER_ID, escape_markdown(f"❌ Error adding feed: {e}", version=2))

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
            bot.send_message(OWNER_ID, escape_markdown(f"✅ Feed removed: {feed_url}", version=2))
        except Exception as e:
            bot.send_message(OWNER_ID, escape_markdown(f"❌ Error removing feed: {e}", version=2))

    @bot.message_handler(commands=['feeds'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def list_feeds_cmd(msg):
        print("📋 /feeds command triggered")
        feeds = get_feeds()
        if not feeds:
            bot.reply_to(msg, escape_markdown("No feeds found", version=2))
        else:
            feed_list = "\n".join([escape_markdown(url, version=2) for url in feeds])
            bot.send_message(msg.chat.id, feed_list, disable_web_page_preview=True)
