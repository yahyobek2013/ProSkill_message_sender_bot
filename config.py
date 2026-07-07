import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_NAME = os.getenv("ADMIN_NAME", "Owner")
GROUP_IDS = [chat_id.strip() for chat_id in os.getenv("GROUP_IDS", "").split(",") if chat_id.strip()]
GROUP_NAMES = [name.strip() for name in os.getenv("GROUP_NAMES", "").split(",") if name.strip()]
if len(GROUP_NAMES) != len(GROUP_IDS):
    GROUP_NAMES = [f"Group {chat_id}" for chat_id in GROUP_IDS]
GROUP_MAP = dict(zip(GROUP_IDS, GROUP_NAMES))
MEDIA_FOLDER = os.getenv("MEDIA_FOLDER", "./media")
DB_PATH = os.getenv("DB_PATH", "./database/database.sqlite")
