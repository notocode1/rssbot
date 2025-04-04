# commands.py

from aiogram import Router, types
from aiogram.types import Message
from config import OWNER_ID, BOT_TOKEN
from db import add_feed, remove_feed, get_feeds, get_groups
from utils import escape_markdown
import feedparser

router = Router()
print("[DEBUG] 🔥 Commands.py is LIVE")

bot_id = BOT_TOKEN.split(":")[0]

def is_owner(msg: Message) -> bool:
    is_me = msg.from_user.id == OWNER_ID
    is_private = msg.chat.type == "private"
    print(f"[CHECK] is_owner: is_me={is_me}, is_private={is_private}")
    return is_me and is_private

@router.message(lambda msg: msg.text and msg.text.startswith("/alive"))
async def cmd_alive(msg: Message):
    print("[DEBUG] /alive handler triggered")
    print("[DEBUG] Full message:", msg.model_dump_json(indent=2))
    if not is_owner(msg):
        print("[BLOCKED] Not owner or not private chat")
        return
    try:
        await msg.reply("✅ Bot is alive and running.")
        print("[SENT] Alive message sent")
    except Exception as e:
        print(f"[ERROR] Failed to send alive message: {e}")

@router.message(lambda msg: msg.text and msg.text.startswith("/feeds"))
async def cmd_feeds(msg: Message):
    print("[DEBUG] /feeds handler triggered")
    if not is_owner(msg):
        print("[BLOCKED] Not owner or not private chat")
        return
    try:
        feeds = get_feeds(bot_id)
        if not feeds:
            await msg.reply("No feeds found.")
            print("[INFO] No feeds to show")
        else:
            text = "\n".join([escape_markdown(url) for url in feeds])
            await msg.answer(text, disable_web_page_preview=True)
            print("[SENT] Feed list sent")
    except Exception as e:
        print(f"[ERROR] /feeds command failed: {e}")

@router.message(lambda msg: msg.text and msg.text.startswith("/add"))
async def cmd_add(msg: Message):
    print("[DEBUG] /add handler triggered")
    print("[DEBUG] Message content:", msg.text)
    if not is_owner(msg):
        print("[BLOCKED] Not owner or not private chat")
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
        add_feed(bot_id, url)
        await msg.reply("✅ Feed added successfully.")
        print("[SENT] Feed added")
    except Exception as e:
        print(f"[ERROR] /add failed: {e}")

@router.message(lambda msg: msg.text and msg.text.startswith("/remove"))
async def cmd_remove(msg: Message):
    print("[DEBUG] /remove handler triggered")
    print("[DEBUG] Message content:", msg.text)
    if not is_owner(msg):
        print("[BLOCKED] Not owner or not private chat")
        return
    parts = msg.text.split(" ", 1)
    if len(parts) < 2:
        await msg.reply("Usage: /remove <rss_url>")
        return
    url = parts[1].strip()
    try:
        remove_feed(bot_id, url)
        await msg.reply("🗑️ Feed removed successfully.")
        print("[SENT] Feed removed")
    except Exception as e:
        print(f"[ERROR] /remove failed: {e}")

@router.message(lambda msg: msg.text and msg.text.startswith("/stats"))
async def cmd_stats(msg: Message):
    print("[DEBUG] /stats handler triggered")
    if not is_owner(msg):
        print("[BLOCKED] Not owner or not private chat")
        return
    try:
        groups = len(get_groups(bot_id))
        feeds = len(get_feeds(bot_id))
        text = (
            f"📊 *Bot Stats*\n\n"
            f"👥 Groups: *{groups}*\n"
            f"🛱 Feeds: *{feeds}*"
        )
        await msg.answer(escape_markdown(text), parse_mode="MarkdownV2")
        print("[SENT] Stats sent")
    except Exception as e:
        print(f"[ERROR] /stats failed: {e}")

@router.message(lambda msg: msg.text and msg.text.startswith("/broadcast"))
async def cmd_broadcast(msg: Message):
    print("[DEBUG] /broadcast handler triggered")
    if not is_owner(msg):
        print("[BLOCKED] Not owner or not private chat")
        return
    parts = msg.text.split(" ", 1)
    if len(parts) < 2:
        await msg.reply("Usage: /broadcast <message>")
        return
    text = parts[1]
    try:
        groups = get_groups(bot_id)
        count = 0
        for chat_id in groups:
            try:
                await msg.bot.send_message(chat_id, text)
                count += 1
            except Exception as e:
                print(f"[BROADCAST ERROR] {chat_id}: {e}")
        await msg.reply(f"📢 Message sent to {count} groups.")
        print(f"[SENT] Broadcast to {count} groups")
    except Exception as e:
        print(f"[ERROR] /broadcast failed: {e}")

# Fallback — anything else
@router.message()
async def debug_catch_all(msg: Message):
    print("[DEBUG] Unmatched message:")
    print(msg.model_dump_json(indent=2))
