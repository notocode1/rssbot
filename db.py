# db.py

import psycopg2
import psycopg2.pool
from typing import List
from config import DB_URL

# Connection Pool (works with multiple bots)
db_pool = psycopg2.pool.ThreadedConnectionPool(minconn=1, maxconn=20, dsn=DB_URL)

# Safer connection decorator
def with_db(func):
    def wrapper(*args, **kwargs):
        try:
            conn = db_pool.getconn()
            result = func(conn, *args, **kwargs)
            return result
        except Exception as e:
            print(f"[DB ERROR] {e}")
            raise
        finally:
            if 'conn' in locals():
                try:
                    db_pool.putconn(conn)
                except Exception as e:
                    print(f"[DB RETURN ERROR] {e}")
    return wrapper

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

# GROUPS

@with_db
def save_group(conn, bot_id: str, chat_id: int, title: str, chat_type: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM groups WHERE bot_id = %s AND chat_id = %s", (bot_id, chat_id))
    exists = cur.fetchone() is not None
    if not exists:
        cur.execute("""
            INSERT INTO groups (bot_id, chat_id, title, type)
            VALUES (%s, %s, %s, %s)
        """, (bot_id, chat_id, title, chat_type))
        conn.commit()
        return True
    return False

@with_db
def get_groups(conn, bot_id: str) -> List[int]:
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM groups WHERE bot_id = %s", (bot_id,))
    return [r[0] for r in cur.fetchall()]

# FEEDS

@with_db
def get_feeds(conn, bot_id: str) -> List[str]:
    cur = conn.cursor()
    cur.execute("SELECT url FROM feeds WHERE bot_id = %s", (bot_id,))
    return [r[0] for r in cur.fetchall()]

@with_db
def add_feed(conn, bot_id: str, url: str):
    cur = conn.cursor()
    cur.execute("INSERT INTO feeds (bot_id, url) VALUES (%s, %s) ON CONFLICT DO NOTHING", (bot_id, url))
    conn.commit()

@with_db
def remove_feed(conn, bot_id: str, url: str):
    cur = conn.cursor()
    cur.execute("DELETE FROM feeds WHERE bot_id = %s AND url = %s", (bot_id, url))
    conn.commit()

# SEEN LINKS

@with_db
def is_seen(conn, bot_id: str, link: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM seen_links WHERE bot_id = %s AND link = %s", (bot_id, link))
    return cur.fetchone() is not None

@with_db
def mark_seen(conn, bot_id: str, link: str):
    cur = conn.cursor()
    cur.execute("INSERT INTO seen_links (bot_id, link) VALUES (%s, %s) ON CONFLICT DO NOTHING", (bot_id, link))
    conn.commit()
