"""Configuration for FastAPI backend."""

from dotenv import load_dotenv
import os

load_dotenv()

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
    raise ValueError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set in .env")

# CORS configuration for Phase 2 (local development only)
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

# Telegram Bot token — only required when running the Telegram bot process.
# The FastAPI server starts normally even if this variable is absent.
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
