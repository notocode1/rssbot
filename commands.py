# commands.py
from config import OWNER_ID
from telebot import TeleBot
from db import add_feed, remove_feed, get_feeds, get_groups
from utils import escape_markdown

def register_commands(bot: TeleBot):
    @bot.message_handler(commands=['add'])
    def add_feed_cmd(msg):
        if msg.from_user.id != OWNER_ID: return
        parts = msg.text.split(" ", 1)
        if len(parts) < 2:
            bot.reply_to(msg, escape_markdown("Usage: /add <rss_url>"))
            return
        add_feed(parts[1].strip())
        bot.reply_to(msg, "✅ Feed added.")

    @bot.message_handler(commands=['remove'])
    def remove_feed_cmd(msg):
        if msg.from_user.id != OWNER_ID: return
        parts = msg.text.split(" ", 1)
        if len(parts) < 2:
            bot.reply_to(msg, escape_markdown("Usage: /remove <rss_url>"))
            return
        remove_feed(parts[1].strip())
        bot.reply_to(msg, "🗑️ Feed removed.")

    @bot.message_handler(commands=['feeds'])
    def list_feeds_cmd(msg):
        if msg.from_user.id != OWNER_ID: return
        feeds = get_feeds()
        if not feeds:
            bot.reply_to(msg, "No feeds found.")
        else:
            feed_list = "\n".join([escape_markdown(url) for url in feeds])
            bot.send_message(msg.chat.id, feed_list, disable_web_page_preview=True)

    @bot.message_handler(commands=['alive'])
    def alive_cmd(msg):
        if msg.from_user.id != OWNER_ID: return
        bot.send_message(msg.chat.id, "✅ Bot is alive.")

    @bot.message_handler(commands=['stats'])
    def stats_cmd(msg):
        if msg.from_user.id != OWNER_ID: return
        groups = len(get_groups())
        feeds = len(get_feeds())
        bot.send_message(msg.chat.id, f"👥 Groups: {groups}\n📡 Feeds: {feeds}")
