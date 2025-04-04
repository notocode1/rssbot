# main.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import init_db
from loop import run_feed_loop
from group import router as group_router
from commands import router as command_router

# Setup logging (Railway console will show this)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Init bot + dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode="MarkdownV2")
dp = Dispatcher()

# Register routers
dp.include_router(group_router)
dp.include_router(command_router)

async def main():
    # Init DB tables
    init_db()

    # Get this bot's unique ID
    bot_id = BOT_TOKEN.split(":")[0]

    # Start feed loop (background task)
    asyncio.create_task(run_feed_loop(bot_id))

    logger.info("🚀 Bot is up and running.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Bot stopped.")
