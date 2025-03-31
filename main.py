import telebot
import feedparser
import time
import threading
import sqlite3
import os
from typing import List, Optional

# ====== CONFIG ======
OWNER_ID = 6478535414  # Replace with your Telegram numeric ID
BOT_TOKENS = [
    '7993876090:AAEK5MqWaF_cnc5E5KcMzGpbtOtLeEh3cmg',
    '7571485933:AAENqnDbWTima0s7y8pFRrj5N58OSFDtnYk',
    # Add more tokens as needed
]
CHECK_INTERVAL = 60  # seconds between checks
MAX_ENTRIES = 5  # max entries per feed check

# ====== DATABASE SETUP ======
db = sqlite3.connect("rss_multi_bot.db", check_same_thread=False)
db.execute("PRAGMA journal_mode=WAL")  # Better concurrent access

# Schema creation with same structure as original
for table in [
    "CREATE TABLE IF NOT EXISTS feeds (token TEXT, url TEXT, PRIMARY KEY (token, url))",
    "CREATE TABLE IF NOT EXISTS subscribers (token TEXT, chat_id INTEGER, PRIMARY KEY (token, chat_id))",
    "CREATE TABLE IF NOT EXISTS sent_links (token TEXT, link TEXT, PRIMARY KEY (token, link))"
]:
    cur.execute(table)
db.commit()

# ====== DB HELPERS ======
def add_feed(token: str, url: str) -> None:
    with db:
        db.execute("INSERT OR IGNORE INTO feeds (token, url) VALUES (?, ?)", (token, url))

def get_feeds(token: str) -> List[str]:
    with db:
        return [r[0] for r in db.execute("SELECT url FROM feeds WHERE token = ?", (token,))]

def add_subscriber(token: str, chat_id: int) -> None:
    with db:
        db.execute("INSERT OR IGNORE INTO subscribers (token, chat_id) VALUES (?, ?)", (token, chat_id))

def remove_subscriber(token: str, chat_id: int) -> None:
    with db:
        db.execute("DELETE FROM subscribers WHERE token = ? AND chat_id = ?", (token, chat_id))

def get_subscribers(token: str) -> List[int]:
    with db:
        return [r[0] for r in db.execute("SELECT chat_id FROM subscribers WHERE token = ?", (token,))]

def mark_sent(token: str, link: str) -> None:
    with db:
        db.execute("INSERT OR IGNORE INTO sent_links (token, link) VALUES (?, ?)", (token, link))

def is_sent(token: str, link: str) -> bool:
    with db:
        return db.execute("SELECT 1 FROM sent_links WHERE token = ? AND link = ?", (token, link)).fetchone() is not None

def cleanup_sent_links(token: str, max_age: int = 24*60*60) -> None:
    """Remove old links if there are more than 1000 (just a safety limit)"""
    with db:
        db.execute("DELETE FROM sent_links WHERE token = ? AND EXISTS (SELECT 1 FROM sent_links WHERE token = ? LIMIT -1 OFFSET 1000)", (token, token))

# ====== BOT SETUP ======
class RSSBot:
    def __init__(self, token: str, delay_index: int):
        self.token = token
        self.bot = telebot.TeleBot(token)
        self.delay_index = delay_index
        self.setup_handlers()

        # 💥 FIX: Remove webhook to allow polling
        try:
            self.bot.remove_webhook()
        except Exception as e:
            print(f"[BOT {self.token}] Failed to remove webhook: {e}")

        threading.Thread(target=self.bot.polling, name=f"poll_{token}", daemon=True).start()
        threading.Thread(target=self.feed_loop, name=f"feeds_{token}", daemon=True).start()


    def setup_handlers(self) -> None:
        bot = self.bot

        @bot.message_handler(commands=['start'])
        def start_handler(msg):
            if not self.check_owner(msg): return
            add_subscriber(self.token, msg.chat.id)
            bot.reply_to(msg, "✅ Subscribed to this bot's updates.")

        @bot.message_handler(commands=['stop'])
        def stop_handler(msg):
            if not self.check_owner(msg): return
            remove_subscriber(self.token, msg.chat.id)
            bot.reply_to(msg, "❌ Unsubscribed from this bot's updates.")

        @bot.message_handler(commands=['add'])
        def add_handler(msg):
            if not self.check_owner(msg): return
            parts = msg.text.split(" ", 1)
            if len(parts) < 2:
                bot.reply_to(msg, "Usage: /add <rss_url>")
                return
            url = parts[1].strip()
            add_feed(self.token, url)
            bot.reply_to(msg, f"✅ Feed added: {url}")

        @bot.message_handler(commands=['feeds'])
        def feeds_handler(msg):
            if not self.check_owner(msg): return
            feeds = get_feeds(self.token)
            bot.reply_to(msg, "\n".join(feeds) if feeds else "No feeds added yet.")

        @bot.chat_member_handler()
        def added_to_group(msg):
            add_subscriber(self.token, msg.chat.id)

        @bot.my_chat_member_handler()
        def added_as_admin(msg):
            add_subscriber(self.token, msg.chat.id)

    def check_owner(self, msg) -> bool:
        return msg.from_user.id == OWNER_ID

    def feed_loop(self) -> None:
        time.sleep(self.delay_index * CHECK_INTERVAL * 8)  # Initial stagger
        while True:
            feeds = get_feeds(self.token)
            if not feeds:
                time.sleep(CHECK_INTERVAL)
                continue

            try:
                for feed_url in feeds:
                    feed = feedparser.parse(feed_url)
                    if feed.bozo:
                        print(f"[BOT {self.token}] Feed error: {feed.bozo_exception}")
                        continue
                    
                    for entry in feed.entries[:MAX_ENTRIES]:
                        if not hasattr(entry, 'link') or not hasattr(entry, 'title'):
                            continue
                        if not is_sent(self.token, entry.link):
                            text = f"📰 {entry.title}\n{entry.link}"
                            for cid in get_subscribers(self.token):
                                try:
                                    self.bot.send_message(cid, text)
                                    time.sleep(0.5)  # Rate limiting
                                except telebot.apihelper.ApiTelegramException as e:
                                    if e.error_code == 403:  # Bot was blocked/removed
                                        remove_subscriber(self.token, cid)
                                    print(f"[BOT {self.token}] Send failed to {cid}: {e}")
                            mark_sent(self.token, entry.link)
                cleanup_sent_links(self.token)
            except Exception as e:
                print(f"[BOT {self.token}] Error: {e}")
            time.sleep(CHECK_INTERVAL)

# ====== START BOTS ======
bots = [RSSBot(tok, idx) for idx, tok in enumerate(BOT_TOKENS)]
print("✅ All bots are running...")
while True:
    time.sleep(60)
