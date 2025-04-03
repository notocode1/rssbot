# db.py
import psycopg2
import psycopg2.pool
from typing import List
from config import DB_URL, BOT_ID

db_pool = psycopg2.pool.ThreadedConnectionPool(1, 20, DB_URL)

def with_db(func):
    def wrapper(*args, **kwargs):
        conn = db_pool.getconn()
        try:
            return func(conn, *args, **kwargs)
        finally:
            db_pool.putconn(conn)
    return wrapper

@with_db
def init_db(conn):
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS groups (
        bot_id TEXT, chat_id BIGINT, title TEXT, type TEXT,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (bot_id, chat_id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS feeds (
        bot_id TEXT, url TEXT, PRIMARY KEY (bot_id, url)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS seen_links (
        bot_id TEXT, link TEXT, date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (bot_id, link)
    )""")
    conn.commit()

@with_db
def save_group(conn, chat_id, title, chat_type):
    cur = conn.cursor()
    cur.execute("INSERT INTO groups (bot_id, chat_id, title, type) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (BOT_ID, chat_id, title, chat_type))
    conn.commit()

@with_db
def get_groups(conn) -> List[int]:
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM groups WHERE bot_id = %s", (BOT_ID,))
    return [r[0] for r in cur.fetchall()]

@with_db
def get_feeds(conn) -> List[str]:
    cur = conn.cursor()
    cur.execute("SELECT url FROM feeds WHERE bot_id = %s", (BOT_ID,))
    return [r[0] for r in cur.fetchall()]

@with_db
def add_feed(conn, url):
    cur = conn.cursor()
    cur.execute("INSERT INTO feeds (bot_id, url) VALUES (%s, %s) ON CONFLICT DO NOTHING", (BOT_ID, url))
    conn.commit()

@with_db
def remove_feed(conn, url):
    cur = conn.cursor()
    cur.execute("DELETE FROM feeds WHERE bot_id = %s AND url = %s", (BOT_ID, url))
    conn.commit()

@with_db
def is_seen(conn, link) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM seen_links WHERE bot_id = %s AND link = %s", (BOT_ID, link))
    return cur.fetchone() is not None

@with_db
def mark_seen(conn, link):
    cur = conn.cursor()
    cur.execute("INSERT INTO seen_links (bot_id, link) VALUES (%s, %s) ON CONFLICT DO NOTHING", (BOT_ID, link))
    conn.commit()

@with_db
def get_last_seen_time(conn):
    cur = conn.cursor()
    cur.execute("SELECT MAX(date_added) FROM seen_links WHERE bot_id = %s", (BOT_ID,))
    result = cur.fetchone()
    return result[0].timestamp() if result and result[0] else None

@with_db
def is_group_saved(conn, chat_id) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM groups WHERE bot_id = %s AND chat_id = %s", (BOT_ID, chat_id))
    return cur.fetchone() is not None
