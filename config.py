# config.py

import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "7645110484:AAFzTPA1T6SoNjUgevx8T_1IIP2NAq3810A")
OWNER_ID = int(os.getenv("OWNER_ID", "6478535414"))
DB_URL = os.getenv("DATABASE_URL", "postgresql://Beon_owner:npg_sYXn3CLrKA4N@ep-shy-recipe-a5azsc70-pooler.us-east-2.aws.neon.tech/Beon?sslmode=require")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 108))  # 3 hours
MAX_ENTRIES = 5
MAX_TEXT_LENGTH = 1000  # match your strict rule

if not BOT_TOKEN or not DB_URL:
    raise ValueError("BOT_TOKEN and DB_URL must be set.")
