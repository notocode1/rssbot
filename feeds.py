import time
import feedparser
from db import get_feeds, get_groups, is_seen, mark_seen
from utils import escape_markdown
from bs4 import BeautifulSoup
from urllib.parse import urlparse

MAX_ENTRIES = 5
MAX_TEXT_LENGTH = 4000
CHECK_INTERVAL = 60

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

def start_feed_loop(bot, bot_id, start_time):
    while True:
        try:
            feeds = get_feeds(bot_id)
            for url in feeds:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:MAX_ENTRIES]:
                        entry_time = time.mktime(entry.published_parsed) if 'published_parsed' in entry else None
                        if entry_time and entry_time < start_time:
                            continue  # Skip old posts

                        link = entry.get('link')
                        if not link or is_seen(bot_id, link):
                            continue
                        mark_seen(bot_id, link)

                        title = escape_markdown(entry.get('title', 'No title'), version=2)
                        summary = escape_markdown(BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text(), version=2)
                        source = escape_markdown(urlparse(link).netloc.replace('www.', '').split('.')[0].capitalize(), version=2)
                        image_url = extract_image(entry)

                        text = f"\U0001F4F0 *{source}*\n\n*{title}*"
                        if summary and len(f"{text}\n\n{summary}\n\n[Read more]({link})") <= MAX_TEXT_LENGTH:
                            text += f"\n\n{summary}\n\n[Read more]({escape_markdown(link, version=2)})"
                        else:
                            text += f"\n\n[Read more]({escape_markdown(link, version=2)})"

                        for chat_id in get_groups(bot_id):
                            try:
                                if image_url:
                                    bot.send_photo(chat_id, image_url, caption=text, parse_mode='MarkdownV2')
                                else:
                                    bot.send_message(chat_id, text, parse_mode='MarkdownV2', disable_web_page_preview=False)
                                time.sleep(0.5)
                            except Exception as e:
                                print(f"Telegram send error in chat {chat_id}: {e}")
                except Exception as e:
                    print(f"Feed error from {url}: {e}")
        except Exception as e:
            print(f"Feed loop error: {e}")
        time.sleep(CHECK_INTERVAL)
