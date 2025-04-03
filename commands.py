from config import OWNER_ID
from telebot import TeleBot
from db import add_feed, remove_feed, get_feeds, get_groups
from utils import escape_markdown

def register_commands(bot: TeleBot, bot_id: str):

    @bot.message_handler(commands=['alive'])
    def alive_cmd(msg):
        print(f"⚡ /alive hit by user: {msg.from_user.id}")
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
            add_feed(bot_id, feed_url)
            bot.send_message(OWNER_ID, escape_markdown(f"✅ Feed added:\n{feed_url}", version=2))
        except Exception as e:
            bot.send_message(OWNER_ID, escape_markdown(f"❌ Error adding feed:\n{e}", version=2))

    @bot.message_handler(commands=['remove'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def remove_feed_cmd(msg):
        print(f"🗑️ /remove command: {msg.text}")
        parts = msg.text.split(" ", 1)
        if len(parts) < 2:
            bot.reply_to(msg, escape_markdown("Usage: /remove <rss_url>", version=2))
            return
        feed_url = parts[1].strip()
        try:
            remove_feed(bot_id, feed_url)
            bot.send_message(OWNER_ID, escape_markdown(f"🗑️ Feed removed:\n{feed_url}", version=2))
        except Exception as e:
            bot.send_message(OWNER_ID, escape_markdown(f"❌ Error removing feed:\n{e}", version=2))

    @bot.message_handler(commands=['feeds'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def list_feeds_cmd(msg):
        print("📋 /feeds command triggered")
        try:
            feeds = get_feeds(bot_id)
            if not feeds:
                bot.reply_to(msg, escape_markdown("No feeds found", version=2))
            else:
                feed_list = "\n".join([escape_markdown(url, version=2) for url in feeds])
                bot.send_message(msg.chat.id, feed_list, disable_web_page_preview=True)
        except Exception as e:
            bot.send_message(msg.chat.id, escape_markdown(f"❌ Error:\n{e}", version=2))

    @bot.message_handler(commands=['stats'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def stats_cmd(msg):
        print("📊 /stats command triggered")
        try:
            groups = get_groups(bot_id)
            feeds = get_feeds(bot_id)
            text = (
                f"📈 *Bot Stats:*
\n*Groups:* {len(groups)}\n*Feeds:* {len(feeds)}"
            )
            bot.send_message(msg.chat.id, escape_markdown(text, version=2))
        except Exception as e:
            bot.send_message(msg.chat.id, escape_markdown(f"❌ Error:\n{e}", version=2))

    @bot.message_handler(commands=['broadcast'], func=lambda msg: msg.from_user.id == OWNER_ID and msg.chat.type == 'private')
    def broadcast_cmd(msg):
        parts = msg.text.split(" ", 1)
        if len(parts) < 2:
            bot.reply_to(msg, escape_markdown("Usage: /broadcast <message>", version=2))
            return

        message = escape_markdown(parts[1].strip(), version=2)
        success = 0
        failed = 0

        groups = get_groups(bot_id)
        for chat_id in groups:
            try:
                bot.send_message(chat_id, message, parse_mode='MarkdownV2')
                success += 1
            except Exception as e:
                print(f"❌ Failed to send to {chat_id}: {e}")
                failed += 1

        summary = f"📣 Broadcast sent!\n✅ Success: {success}\n❌ Failed: {failed}"
        bot.send_message(OWNER_ID, escape_markdown(summary, version=2))
