# loop.py

import asyncio
import feedparser
import time
from urllib.parse import urlparse
from aiogram import Bot
from config import CHECK_INTERVAL, MAX_ENTRIES, MAX_TEXT_LENGTH, BOT_TOKEN
from db import get_feeds, get_groups, is_seen, mark_seen
from utils import escape_markdown, extract_image, clean_html

bot = Bot(token=BOT_TOKEN, parse_mode="MarkdownV2")

# Track when bot starts (only post articles published after this)
start_time = time.time()

async def run_feed_loop(bot_id: str):
    while True:
        try:
            print(f"[LOOP] Checking feeds for bot_id={bot_id}")
            feeds = get_feeds(bot_id)
            for url in feeds:
                try:
                    feed = feedparser.parse(url)
                    count = 0  # track how many articles we posted per feed

                    for entry in feed.entries:
                        if count >= MAX_ENTRIES:
                            break  # respect max posts per site

                        link = entry.get('link')
                        if not link:
                            continue

                        # Check publish time
                        published_time = time.mktime(entry.published_parsed) if 'published_parsed' in entry else None
                        if published_time is None or published_time < start_time:
                            continue

                        # Format content
                        title = escape_markdown(entry.get('title', 'No Title'))
                        summary = escape_markdown(clean_html(entry.get('summary', '')))
                        source = escape_markdown(urlparse(link).netloc.replace('www.', '').split('.')[0].capitalize())
                        image_url = extract_image(entry)

                        text = f"📰 *{source}*\n\n*{title}*"
                        full_text = f"{text}\n\n{summary}\n\n[Read more]({link})"

                        if not image_url:
                            print(f"[SKIP] No image found for: {link}")
                            continue

                        if len(full_text) > 1000:
                            print(f"[SKIP] Too long ({len(full_text)} chars): {link}")
                            continue

                        if is_seen(bot_id, link):
                            continue  # already posted

                        mark_seen(bot_id, link)
                        groups = get_groups(bot_id)

                        for chat_id in groups:
                            try:
                                await bot.send_photo(chat_id, image_url, caption=full_text)
                                print(f"[POSTED] Sent to {chat_id}")
                                await asyncio.sleep(0.5)
                            except Exception as e:
                                print(f"[ERROR] Failed to send to {chat_id}: {e}")

                        count += 1  # count how many posted for this feed

                except Exception as e:
                    print(f"[ERROR] Feed error for {url}: {e}")

        except Exception as e:
            print(f"[FATAL] Loop error: {e}")

        print(f"[SLEEP] Sleeping {CHECK_INTERVAL} seconds...")
        await asyncio.sleep(CHECK_INTERVAL)
