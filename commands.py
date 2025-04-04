# commands.py

from aiogram import Router, types
from aiogram.types import Message
from config import OWNER_ID, BOT_TOKEN
from db import add_feed, remove_feed, get_feeds, get_groups
from utils import escape_markdown
import feedparser

router = Router()

bot_id = BOT_TOKEN.split(":")[0]

# Utility to check if sender is the owner
def is_owner(msg: Message) -> bool:
    return msg.from_user.id == OWNER_ID

# /add <rss_url>
@router.message(lambda msg: msg.text.startswith("/add"))
async def cmd_add(msg: Message):
    if not is_owner(msg):
        return

    parts = msg.text.split(" ", 1)
    if len(parts) < 2:
        await msg.reply("Usage: /add <rss_url>")
        return

    url = parts[1].strip()
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            await msg.reply("❌ Invalid or empty RSS feed.")
            return
    except Exception:
        await msg.reply("❌ Failed to parse the feed.")
        return

    add_feed(bot_id, url)
    await msg.reply("✅ Feed added successfully.")

# /remove <rss_url>
@router.message(lambda msg: msg.text.startswith("/remove"))
async def cmd_remove(msg: Message):
    if not is_owner(msg):
        return

    parts = msg.text.split(" ", 1)
    if len(parts) < 2:
        await msg.reply("Usage: /remove <rss_url>")
        return

    url = parts[1].strip()
    remove_feed(bot_id, url)
    await msg.reply("🗑️ Feed removed successfully.")

# /feeds
@router.message(lambda msg: msg.text == "/feeds")
async def cmd_feeds(msg: Message):
    if not is_owner(msg):
        return

    feeds = get_feeds(bot_id)
    if not feeds:
        await msg.reply("No feeds found.")
    else:
        text = "\n".join([escape_markdown(url) for url in feeds])
        await msg.answer(text, disable_web_page_preview=True)

# /alive (debug mode)
@router.message(lambda msg: msg.text == "/alive")
async def cmd_alive(msg: Message):
    print(f"[DEBUG] /alive called by user ID: {msg.from_user.id}")

    if not is_owner(msg):
        print(f"[DENIED] Not the owner: {msg.from_user.id}")
        return

    await msg.reply("✅ Bot is alive and running.")

# /stats
@router.message(lambda msg: msg.text == "/stats")
async def cmd_stats(msg: Message):
    if not is_owner(msg):
        return

    groups = len(get_groups(bot_id))
    feeds = len(get_feeds(bot_id))

    text = (
        f"📊 *Bot Stats*\n\n"
        f"👥 Groups: *{groups}*\n"
        f"📡 Feeds: *{feeds}*"
    )
    await msg.answer(escape_markdown(text), parse_mode="MarkdownV2")

# /broadcast <message>
@router.message(lambda msg: msg.text.startswith("/broadcast"))
async def cmd_broadcast(msg: Message):
    if not is_owner(msg):
        return

    parts = msg.text.split(" ", 1)
    if len(parts) < 2:
        await msg.reply("Usage: /broadcast <message>")
        return

    text = parts[1]
    groups = get_groups(bot_id)
    count = 0

    for chat_id in groups:
        try:
            await msg.bot.send_message(chat_id, text)
            count += 1
        except Exception as e:
            print(f"[BROADCAST ERROR] {chat_id}: {e}")

    await msg.reply(f"📢 Message sent to {count} groups.")
