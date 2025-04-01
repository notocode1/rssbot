import telebot
import feedparser
import time
import threading
import psycopg2
import psycopg2.pool
import requests
import os
import re

from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# ====== CONFIG ======
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", "6478535414"))
DB_URL = os.environ.get("DB_URL")
CHECK_INTERVAL = 60
MAX_ENTRIES = 5
MAX_TEXT_LENGTH = 4000

if not BOT_TOKEN or not DB_URL:
    raise ValueError("BOT_TOKEN and DB_URL must be set in environment variables.")

bot_id = BOT_TOKEN.split(":")[0]
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

def escape_markdown(text: str, version: int = 2) -> str:
    if not text:
        return ''
    if version == 2:
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    return text

@with_db
def init_db(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            bot_id TEXT,
            chat_id BIGINT,
            title TEXT,
            type TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (bot_id, chat_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feeds (
            bot_id TEXT,
            url TEXT,
            PRIMARY KEY (bot_id, url)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seen_links (
            bot_id TEXT,
            link TEXT,
            PRIMARY KEY (bot_id, link)
        )
    """)
    conn.commit()

@with_db
def save_group(conn, chat_id: int, title: str, chat_type: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM groups WHERE bot_id = %s AND chat_id = %s", (bot_id, chat_id))
    exists = cur.fetchone() is not None
    if not exists:
        cur.execute("""
            INSERT INTO groups (bot_id, chat_id, title, type) VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (bot_id, chat_id, title, chat_type))
        conn.commit()
        return True
    return False

@with_db
def get_groups(conn) -> List[int]:
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM groups WHERE bot_id = %s", (bot_id,))
    return [r[0] for r in cur.fetchall()]

@with_db
def get_feeds(conn) -> List[str]:
    cur = conn.cursor()
    cur.execute("SELECT url FROM feeds WHERE bot_id = %s", (bot_id,))
    return [r[0] for r in cur.fetchall()]

@with_db
def add_feed(conn, url: str):
    cur = conn.cursor()
    cur.execute("INSERT INTO feeds (bot_id, url) VALUES (%s, %s) ON CONFLICT DO NOTHING", (bot_id, url))
    conn.commit()

@with_db
def remove_feed(conn, url: str):
    cur = conn.cursor()
    cur.execute("DELETE FROM feeds WHERE bot_id = %s AND url = %s", (bot_id, url))
    conn.commit()

@with_db
def is_seen(conn, link: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM seen_links WHERE bot_id = %s AND link = %s", (bot_id, link))
    return cur.fetchone() is not None

@with_db
def mark_seen(conn, link: str):
    cur = conn.cursor()
    cur.execute("INSERT INTO seen_links (bot_id, link) VALUES (%s, %s) ON CONFLICT DO NOTHING", (bot_id, link))
    conn.commit()

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

init_db()
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='MarkdownV2')

@bot.message_handler(commands=['add'])
def add_feed_cmd(msg):
    if msg.from_user.id != OWNER_ID:
        return
    parts = msg.text.split(" ", 1)
    if len(parts) < 2:
        bot.reply_to(msg, escape_markdown("Usage: /add <rss_url>", version=2))
        return
    url = parts[1].strip()
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            bot.reply_to(msg, escape_markdown("Invalid or empty RSS feed.", version=2))
            return
    except Exception:
        bot.reply_to(msg, escape_markdown("Failed to validate RSS feed.", version=2))
        return
    add_feed(url)
    bot.reply_to(msg, escape_markdown("✅ Feed added successfully.", version=2))

@bot.message_handler(commands=['remove'])
def remove_feed_cmd(msg):
    if msg.from_user.id != OWNER_ID:
        return
    parts = msg.text.split(" ", 1)
    if len(parts) < 2:
        bot.reply_to(msg, escape_markdown("Usage: /remove <rss_url>", version=2))
        return
    url = parts[1].strip()
    remove_feed(url)
    bot.reply_to(msg, escape_markdown("🗑️ Feed removed successfully.", version=2))

@bot.message_handler(commands=['feeds'])
def list_feeds_cmd(msg):
    if msg.from_user.id != OWNER_ID:
        return
    feeds = get_feeds()
    if not feeds:
        bot.reply_to(msg, escape_markdown("No feeds found.", version=2))
    else:
        feed_list = "\n".join([escape_markdown(url, version=2) for url in feeds])
        bot.send_message(msg.chat.id, feed_list, disable_web_page_preview=True)

@bot.message_handler(commands=['alive'])
def alive_cmd(msg):
    if msg.from_user.id != OWNER_ID:
        return
    bot.send_message(msg.chat.id, escape_markdown("✅ Bot is alive and working.", version=2))

@bot.message_handler(func=lambda msg: msg.chat.type in ['group', 'supergroup'])
def auto_save_group(msg):
    if save_group(msg.chat.id, msg.chat.title, msg.chat.type):
        text = (
            f"🆕 *New Group Saved*\n\n"
            f"*Title:* {escape_markdown(msg.chat.title, version=2)}\n"
            f"*Chat ID:* `{msg.chat.id}`\n"
            f"*Type:* `{msg.chat.type}`"
        )
        bot.send_message(OWNER_ID, text)

def feed_loop():
    while True:
        try:
            feeds = get_feeds()
            for url in feeds:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:MAX_ENTRIES]:
                        link = entry.get('link')
                        if not link or is_seen(link):
                            continue
                        mark_seen(link)

                        title = escape_markdown(entry.get('title', 'No title'), version=2)
                        summary = escape_markdown(BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text(), version=2)
                        source = escape_markdown(urlparse(link).netloc.replace('www.', '').split('.')[0].capitalize(), version=2)
                        image_url = extract_image(entry)

                        text = f"\U0001F4F0 *{source}*\n\n*{title}*"
                        if summary and len(f"{text}\n\n{summary}\n\n[Read more]({link})") <= MAX_TEXT_LENGTH:
                            text += f"\n\n{summary}\n\n[Read more]({link})"
                        else:
                            text += f"\n\n[Read more]({link})"

                        for chat_id in get_groups():
                            try:
                                if image_url:
                                    bot.send_photo(chat_id, image_url, caption=text)
                                else:
                                    bot.send_message(chat_id, text, disable_web_page_preview=False)
                                time.sleep(0.5)
                            except Exception as e:
                                print(f"Telegram send error in chat {chat_id}: {e}")
                except Exception as e:
                    print(f"Feed error from {url}: {e}")
        except Exception as e:
            print(f"Feed loop error: {e}")
        time.sleep(CHECK_INTERVAL)

threading.Thread(target=feed_loop, daemon=True).start()
bot.infinity_polling()
