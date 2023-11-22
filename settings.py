import logging
import os

from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DB_URI = os.getenv("DB_URI")
LOGS_WEBHOOK_URL = os.getenv("LOGS_WEBHOOK_URL")
