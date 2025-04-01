import telebot
import feedparser
import time
import threading
import sqlite3
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re

# ====== CUSTOM ESCAPE FUNCTION ======
def escape_markdown(text: str, version: int = 2) -> str:
    if not text:
        return ''
    if version == 2:
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    else:
        return re.sub(r'([_*\[\]()~`>#+=|{}.!-])', r'\\\1', text)

# ====== CONFIG ======
OWNER_ID = 6478535414
BOT_TOKENS = [
    '7993876090:AAEK5MqWaF_cnc5E5KcMzGpbtOtLeEh3cmg',
    '7571485933:AAENqnDbWTima0s7y8pFRrj5N58OSFDtnYk',
]
CHECK_INTERVAL = 60
MAX_ENTRIES = 5
MAX_TEXT_LENGTH = 4000

# ====== DATABASE SETUP ======
db = sqlite3.connect("rss_multi_bot.db", check_same_thread=False)
db.execute("PRAGMA journal_mode=WAL")

with db:
    db.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        token TEXT,
        chat_id INTEGER PRIMARY KEY,
        title TEXT,
        type TEXT,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    db.execute("""
    CREATE TABLE IF NOT EXISTS feeds (
        token TEXT,
        url TEXT,
        PRIMARY KEY (token, url)
    )
    """)

# ====== DB HELPERS ======
def save_group(token: str, chat_id: int, title: str, chat_type: str):
    with db:
        db.execute("""
        INSERT OR IGNORE INTO groups (token, chat_id, title, type) VALUES (?, ?, ?, ?)
        """, (token, chat_id, title, chat_type))

def get_groups(token: str) -> List[int]:
    with db:
        return [r[0] for r in db.execute("SELECT chat_id FROM groups WHERE token = ?", (token,))]

def add_feed(token: str, url: str):
    with db:
        db.execute("INSERT OR IGNORE INTO feeds (token, url) VALUES (?, ?)", (token, url))

def remove_feed(token: str, url: str):
    with db:
        db.execute("DELETE FROM feeds WHERE token = ? AND url = ?", (token, url))

def get_feeds(token: str) -> List[str]:
    with db:
        return [r[0] for r in db.execute("SELECT url FROM feeds WHERE token = ?", (token,))]

def extract_image(entry):
    if 'media_content' in entry and entry.media_content:
        return entry.media_content[0].get('url')
    if 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image'):
                return link.get('href')
    soup = BeautifulSoup(entry.get('summary', ''), 'html.parser')
    img = soup.find('img')
    if img and img.get('src'):
        return img['src']
    return None

# ====== BOT SETUP ======
class RSSBot:
    def __init__(self, token: str, delay_index: int):
        self.token = token
        self.bot = telebot.TeleBot(token, parse_mode='MarkdownV2')
        self.delay_index = delay_index
        self.setup_handlers()
        try:
            self.bot.remove_webhook()
        except Exception:
            pass
        threading.Thread(target=self.bot.polling, name=f"poll_{token}", daemon=True).start()
        threading.Thread(target=self.feed_loop, name=f"feeds_{token}", daemon=True).start()

    def setup_handlers(self):
        bot = self.bot

        @bot.message_handler(commands=['broadcast'])
        def broadcast(msg):
            if msg.from_user.id != OWNER_ID:
                return
            parts = msg.text.split(" ", 1)
            if len(parts) < 2:
                bot.reply_to(msg, escape_markdown("Usage: /broadcast <message>"), parse_mode="MarkdownV2")
                return
            message = escape_markdown(parts[1].strip())
            for chat_id in get_groups(self.token):
                try:
                    bot.send_message(chat_id, message, parse_mode='MarkdownV2')
                    time.sleep(0.5)
                except Exception as e:
                    print(f"[BOT {self.token}] Failed to send broadcast to {chat_id}: {e}")

        @bot.message_handler(commands=['add'])
        def add_feed_cmd(msg):
            if msg.from_user.id != OWNER_ID:
                return
            parts = msg.text.split(" ", 1)
            if len(parts) < 2:
                bot.reply_to(msg, escape_markdown("Usage: /add <rss_url>"), parse_mode="MarkdownV2")
                return
            url = parts[1].strip()
            add_feed(self.token, url)
            bot.reply_to(msg, escape_markdown("✅ Feed added successfully."), parse_mode="MarkdownV2")

        @bot.message_handler(commands=['remove'])
        def remove_feed_cmd(msg):
            if msg.from_user.id != OWNER_ID:
                return
            parts = msg.text.split(" ", 1)
            if len(parts) < 2:
                bot.reply_to(msg, escape_markdown("Usage: /remove <rss_url>"), parse_mode="MarkdownV2")
                return
            url = parts[1].strip()
            remove_feed(self.token, url)
            bot.reply_to(msg, escape_markdown("🗑️ Feed removed successfully."), parse_mode="MarkdownV2")

        @bot.message_handler(commands=['feeds'])
        def list_feeds_cmd(msg):
            if msg.from_user.id != OWNER_ID:
                return
            feeds = get_feeds(self.token)
            if not feeds:
                bot.reply_to(msg, escape_markdown("No feeds found."), parse_mode="MarkdownV2")
            else:
                feed_list = escape_markdown("\n".join(feeds), version=2)
                bot.send_message(msg.chat.id, feed_list, parse_mode='MarkdownV2', disable_web_page_preview=True)

        @bot.message_handler(commands=['alive'])
        def alive_cmd(msg):
            if msg.from_user.id != OWNER_ID:
                return
            bot.reply_to(msg, escape_markdown("✅ Bot is alive and working."), parse_mode="MarkdownV2")

        @bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'])
        def auto_save_group(msg):
            save_group(self.token, msg.chat.id, msg.chat.title, msg.chat.type)

    def feed_loop(self):
        time.sleep(self.delay_index * CHECK_INTERVAL * 8)
        seen_links = set()
        while True:
            try:
                feeds = get_feeds(self.token)
                for url in feeds:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:MAX_ENTRIES]:
                        link = entry.get('link')
                        if not link or link in seen_links:
                            continue
                        seen_links.add(link)

                        title = escape_markdown(entry.get('title', 'No title'), version=2)
                        summary = escape_markdown(BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text(), version=2)
                        source_name = escape_markdown(urlparse(link).netloc.replace('www.', ''), version=2)
                        link_escaped = escape_markdown(link, version=2)
                        image_url = extract_image(entry)

                        text = f"*Source: {source_name}*\n\n*{title}*\n\n{summary}\n\n[Read more]({link_escaped})"
                        if len(text) > MAX_TEXT_LENGTH:
                            text = f"*Source: {source_name}*\n\n*{title}*\n\n[Read more]({link_escaped})"

                        for chat_id in get_groups(self.token):
                            try:
                                if image_url:
                                    self.bot.send_photo(chat_id, image_url, caption=text, parse_mode='MarkdownV2')
                                else:
                                    self.bot.send_message(chat_id, text, parse_mode='MarkdownV2', disable_web_page_preview=False)
                                time.sleep(0.5)
                            except Exception as e:
                                print(f"[BOT {self.token}] Failed to send to {chat_id}: {e}")
            except Exception as e:
                print(f"[BOT {self.token}] Feed loop error: {e}")
            time.sleep(CHECK_INTERVAL)

# ====== START ALL BOTS ======
for index, token in enumerate(BOT_TOKENS):
    RSSBot(token, index)

print("✅ Group-only RSS bots running...")
while True:
    time.sleep(60)
