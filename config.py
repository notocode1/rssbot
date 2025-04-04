# config.py

import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
OWNER_ID = int(os.getenv("OWNER_ID", "6478535414"))
DB_URL = os.getenv("DATABASE_URL", "YOUR_DATABASE_URL_HERE")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 180))  # default 3 mins
MAX_ENTRIES = 5
MAX_TEXT_LENGTH = 4000

if not BOT_TOKEN or not DB_URL:
    raise ValueError("BOT_TOKEN and DB_URL must be set.")
