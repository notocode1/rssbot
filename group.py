# group.py

from aiogram import Router, types
from aiogram.types import Message
from config import OWNER_ID, BOT_TOKEN
from db import save_group
from utils import escape_markdown

router = Router()

bot_id = BOT_TOKEN.split(":")[0]

@router.message()
async def detect_group(message: Message):
    # Only care about group/supergroup messages
    if message.chat.type not in ['group', 'supergroup']:
        return

    chat_id = message.chat.id
    title = message.chat.title or "Unknown"
    chat_type = message.chat.type

    # Try to save the group
    saved = save_group(bot_id, chat_id, title, chat_type)

    if saved:
        info = (
            f"🆕 *New Group Saved*\n\n"
            f"*Title:* {escape_markdown(title)}\n"
            f"*Chat ID:* `{chat_id}`\n"
            f"*Type:* `{chat_type}`"
        )

        try:
            await message.bot.send_message(OWNER_ID, info)
            print(f"[GROUP] Saved new group: {title} ({chat_id})")
        except Exception as e:
            print(f"[ERROR] Could not notify owner: {e}")
