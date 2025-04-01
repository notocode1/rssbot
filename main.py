import telebot
import feedparser
import time
import threading
import psycopg2
import psycopg2.pool
import requests
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import os

# ====== CONFIG ======
OWNER_ID = 6478535414
BOT_TOKENS = [
    '8097964400:AAGDsqfURZ8WEpClJLzLCGPIed7p7sKjPh4',  # crypto
    '7645110484:AAHBmNrLChJSdAJTypB6Sz7KWuesAFC_HtQ',  # business
]
DB_URL = os.environ.get("DB_URL")
CHECK_INTERVAL = 60
MAX_ENTRIES = 5
MAX_TEXT_LENGTH = 4000

# ====== DATABASE POOL ======
db_pool = psycopg2.pool.ThreadedConnectionPool(1, 20, DB_URL)

def with_db(func):
    def wrapper(*args, **kwargs):
        conn = db_pool.getconn()
        try:
            result = func(conn, *args, **kwargs)
            return result
        finally:
            db_pool.putconn(conn)
    return wrapper

# ====== ESCAPE FUNCTION ======
def escape_markdown(text: str, version: int = 2) -> str:
    if not text:
        return ''
    if version == 2:
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    return text

# ====== DB INIT ======
@with_db
def init_db(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        token TEXT,
        chat_id BIGINT PRIMARY KEY,
        title TEXT,
        type TEXT,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feeds (
        token TEXT,
        url TEXT,
        PRIMARY KEY (token, url)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS seen_links (
        token TEXT,
        link TEXT,
        PRIMARY KEY (token, link)
    )
    """)
    conn.commit()

init_db()

# ====== DB HELPERS ======
@with_db
def save_group(conn, token: str, chat_id: int, title: str, chat_type: str):
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO groups (token, chat_id, title, type) VALUES (%s, %s, %s, %s)
    ON CONFLICT DO NOTHING
    """, (token, chat_id, title, chat_type))
    conn.commit()

@with_db
def get_groups(conn, token: str) -> List[int]:
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM groups WHERE token = %s", (token,))
    return [r[0] for r in cur.fetchall()]

@with_db
def get_feeds(conn, token: str) -> List[str]:
    cur = conn.cursor()
    cur.execute("SELECT url FROM feeds WHERE token = %s", (token,))
    return [r[0] for r in cur.fetchall()]

@with_db
def add_feed(conn, token: str, url: str):
    cur = conn.cursor()
    cur.execute("INSERT INTO feeds (token, url) VALUES (%s, %s) ON CONFLICT DO NOTHING", (token, url))
    conn.commit()

@with_db
def remove_feed(conn, token: str, url: str):
    cur = conn.cursor()
    cur.execute("DELETE FROM feeds WHERE token = %s AND url = %s", (token, url))
    conn.commit()

@with_db
def is_seen(conn, token: str, link: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM seen_links WHERE token = %s AND link = %s", (token, link))
    return cur.fetchone() is not None

@with_db
def mark_seen(conn, token: str, link: str):
    cur = conn.cursor()
    cur.execute("INSERT INTO seen_links (token, link) VALUES (%s, %s) ON CONFLICT DO NOTHING", (token, link))
    conn.commit()

# ====== IMAGE HANDLER ======
def extract_image(entry):
    if 'media_content' in entry and entry.media_content:
        url = entry.media_content[0].get('url')
        if url and url.lower().endswith(('jpg', 'jpeg', 'png', 'gif')):
            return url
    if 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image'):
                return link.get('href')
    soup = BeautifulSoup(entry.get('summary', ''), 'html.parser')
    img = soup.find('img')
    if img and img.get('src') and img['src'].lower().endswith(('jpg', 'jpeg', 'png', 'gif')):
        return img['src']
    return None

# ====== BOT SETUP ======
class RSSBot:
    def __init__(self, token: str, delay_index: int):
        self.token = token
        self.bot = telebot.TeleBot(token, parse_mode='MarkdownV2')
        self.delay_index = delay_index
        self.setup_handlers()
        threading.Thread(target=self.bot.polling, name=f"poll_{token}", daemon=True).start()
        threading.Thread(target=self.feed_loop, name=f"feeds_{token}", daemon=True).start()

    def setup_handlers(self):
        bot = self.bot

        @bot.message_handler(commands=['add'])
        def add_feed_cmd(msg):
            if msg.from_user.id != OWNER_ID:
                return
            parts = msg.text.split(" ", 1)
            if len(parts) < 2:
                bot.reply_to(msg, escape_markdown("Usage: /add <rss_url>", version=2), parse_mode='MarkdownV2')
                return
            url = parts[1].strip()
            add_feed(self.token, url)
            bot.reply_to(msg, escape_markdown("✅ Feed added successfully.", version=2), parse_mode='MarkdownV2')

        @bot.message_handler(commands=['remove'])
        def remove_feed_cmd(msg):
            if msg.from_user.id != OWNER_ID:
                return
            parts = msg.text.split(" ", 1)
            if len(parts) < 2:
                bot.reply_to(msg, escape_markdown("Usage: /remove <rss_url>", version=2), parse_mode='MarkdownV2')
                return
            url = parts[1].strip()
            remove_feed(self.token, url)
            bot.reply_to(msg, escape_markdown("🗑️ Feed removed successfully.", version=2), parse_mode='MarkdownV2')

        @bot.message_handler(commands=['feeds'])
        def list_feeds_cmd(msg):
            if msg.from_user.id != OWNER_ID:
                return
            feeds = get_feeds(self.token)
            if not feeds:
                bot.reply_to(msg, escape_markdown("No feeds found.", version=2), parse_mode='MarkdownV2')
            else:
                feed_list = "\n".join([escape_markdown(url, version=2) for url in feeds])
                bot.send_message(msg.chat.id, feed_list, parse_mode='MarkdownV2', disable_web_page_preview=True)

        @bot.message_handler(commands=['stats'])
        def stats_cmd(msg):
            if msg.from_user.id != OWNER_ID:
                return
            group_count = len(get_groups(self.token))
            feed_count = len(get_feeds(self.token))
            text = (
                f"*Bot Token:* `{escape_markdown(self.token)}`\n"
                f"*Groups Saved:* *{group_count}*\n"
                f"*Feeds Subscribed:* *{feed_count}*"
            )
            bot.send_message(msg.chat.id, text, parse_mode='MarkdownV2')

        @bot.message_handler(commands=['alive'])
        def alive_cmd(msg):
            if msg.from_user.id != OWNER_ID:
                return
            bot.send_message(msg.chat.id, escape_markdown("✅ Bot is alive and working.", version=2), parse_mode='MarkdownV2')

        @bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'])
        def auto_save_group(msg):
            if msg.new_chat_members:
                for member in msg.new_chat_members:
                    if member.id == bot.get_me().id:
                        save_group(self.token, msg.chat.id, msg.chat.title, msg.chat.type)
                        text = (
                            f"🆕 New Group Saved

"
                            f"*Title:* {escape_markdown(msg.chat.title, version=2)}
"
                            f"*Chat ID:* `{msg.chat.id}`
"
                            f"*Type:* `{msg.chat.type}`
"
                            f"*Token:* `{escape_markdown(self.token)}`"
                        )
                        bot.send_message(OWNER_ID, text, parse_mode='MarkdownV2')
            text = (
                f"🆕 New Group Saved\n\n"
                f"*Title:* {escape_markdown(msg.chat.title, version=2)}\n"
                f"*Chat ID:* `{msg.chat.id}`\n"
                f"*Type:* `{msg.chat.type}`\n"
                f"*Token:* `{escape_markdown(self.token)}`"
            )
            bot.send_message(OWNER_ID, text, parse_mode='MarkdownV2')

    def feed_loop(self):
        feed_failures = {}
        time.sleep(self.delay_index * CHECK_INTERVAL * 8)
        while True:
            try:
                feeds = get_feeds(self.token)
                for url in feeds:
                    try:
                        feed = feedparser.parse(url)
                        for entry in feed.entries[:MAX_ENTRIES]:
                            link = entry.get('link')
                            if not link or is_seen(self.token, link):
                                continue
                            mark_seen(self.token, link)

                            title = escape_markdown(entry.get('title', 'No title'), version=2)
                            summary = escape_markdown(BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text(), version=2)
                            source_name = escape_markdown(urlparse(link).netloc.replace('www.', '').split('.')[0].capitalize(), version=2)
                            link_escaped = escape_markdown(link, version=2)
                            image_url = extract_image(entry)

                            text = f"\U0001F4F0 *{source_name}*\n\n*{title}*"
                            if summary and len(f"{text}\n\n{summary}\n\n[Read more]({link_escaped})") <= MAX_TEXT_LENGTH:
                                text += f"\n\n{summary}\n\n[Read more]({link_escaped})"
                            else:
                                text += f"\n\n[Read more]({link_escaped})"

                            for chat_id in get_groups(self.token):
                                try:
                                    if image_url:
                                        self.bot.send_photo(chat_id, image_url, caption=text, parse_mode='MarkdownV2')
                                    else:
                                        self.bot.send_message(chat_id, text, parse_mode='MarkdownV2', disable_web_page_preview=False)
                                    time.sleep(0.5)
                                except telebot.apihelper.ApiTelegramException as e:
                                    if "kicked" in str(e).lower() or "forbidden" in str(e).lower():
                                        print(f"Bot was removed from chat {chat_id}, skipping.")
                                        continue
                                    print(f"Telegram send error: {e}")
                    except Exception as e:
                        print(f"Feed error from {url}: {e}")
            except Exception as e:
                print(f"Feed loop error: {e}")
            time.sleep(CHECK_INTERVAL)

# ====== START BOTS ======
for index, token in enumerate(BOT_TOKENS):
    RSSBot(token, index)

print("✅ All RSS bots are running...")
while True:
    time.sleep(60)
