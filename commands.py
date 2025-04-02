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
            bot.reply_to(msg, escape_markdown("Usage: /add <rss_url>", version=2))
            return
        add_feed(parts[1].strip())
        bot.reply_to(msg, escape_markdown("✅ Feed added.", version=2))

    @bot.message_handler(commands=['remove'])
    def remove_feed_cmd(msg):
        if msg.from_user.id != OWNER_ID: return
        parts = msg.text.split(" ", 1)
        if len(parts) < 2:
            bot.reply_to(msg, escape_markdown("Usage: /remove <rss_url>", version=2))
            return
        remove_feed(parts[1].strip())
        bot.reply_to(msg, escape_markdown("🗑️ Feed removed.", version=2))

    @bot.message_handler(commands=['feeds'])
    def list_feeds_cmd(msg):
        if msg.from_user.id != OWNER_ID: return
        feeds = get_feeds()
        if not feeds:
            bot.reply_to(msg, escape_markdown("No feeds found.", version=2))
        else:
            feed_list = "\n".join([escape_markdown(url, version=2) for url in feeds])
            bot.send_message(msg.chat.id, feed_list, disable_web_page_preview=True)

    @bot.message_handler(commands=['alive'])
    def alive_cmd(msg):
        if msg.from_user.id != OWNER_ID: return
        bot.send_message(msg.chat.id, escape_markdown("✅ Bot is alive.", version=2))

    @bot.message_handler(commands=['stats'])
    def stats_cmd(msg):
        if msg.from_user.id != OWNER_ID: return
        groups = len(get_groups())
        feeds = len(get_feeds())
        stats_text = (
            f"📊 *Bot Stats*\n\n"
            f"👥 Groups: *{groups}*\n"
            f"📡 Feeds: *{feeds}*"
        )
        bot.send_message(msg.chat.id, escape_markdown(stats_text, version=2), parse_mode='MarkdownV2')
