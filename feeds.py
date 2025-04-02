# feeds.py
import time
import feedparser
from db import get_feeds, get_groups, is_seen, mark_seen
from utils import escape_markdown, extract_image
from config import CHECK_INTERVAL, MAX_ENTRIES, MAX_TEXT_LENGTH
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def start_feed_loop(bot, start_time):
    def loop():
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
                            published_time = time.mktime(entry.published_parsed) if 'published_parsed' in entry else None
                            if published_time and published_time < start_time:
                                continue

                            mark_seen(link)
                            title = escape_markdown(entry.get('title', 'No title'))
                            summary = escape_markdown(BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text())
                            source = escape_markdown(urlparse(link).netloc.replace('www.', '').split('.')[0].capitalize())
                            image_url = extract_image(entry)
                            text = f"📰 *{source}*\n\n*{title}*\n\n{summary}\n\n[Read more]({link})"

                            if len(text) > MAX_TEXT_LENGTH:
                                continue

                            for chat_id in get_groups():
                                try:
                                    if image_url:
                                        bot.send_photo(chat_id, image_url, caption=text)
                                    else:
                                        bot.send_message(chat_id, text, disable_web_page_preview=False)
                                    time.sleep(0.5)
                                except Exception as e:
                                    print(f"[!] Telegram error in chat {chat_id}: {e}")
                    except Exception as e:
                        print(f"[!] Feed error for {url}: {e}")
            except Exception as e:
                print(f"[!] Feed loop error: {e}")
            time.sleep(CHECK_INTERVAL)
    import threading
    threading.Thread(target=loop, daemon=True).start()
