import os
from dotenv import load_dotenv
import socks

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "").strip("@")

# SSH Tunnel/Proxy settings
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() == "true"
PROXY_TYPE = {
    "socks4": socks.SOCKS4,
    "socks5": socks.SOCKS5,
    "http": socks.HTTP
}.get(os.getenv("PROXY_TYPE", "socks5").lower(), socks.SOCKS5)

PROXY_ADDR = os.getenv("PROXY_ADDR", "127.0.0.1")
PROXY_PORT = int(os.getenv("PROXY_PORT", "9000"))
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")

# API Server settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "11434"))

# Session settings
SESSION_NAME = os.getenv("SESSION_NAME", "telegram_session")

# Helper function to get proxy configuration for Telethon


def get_proxy_settings():
    if not PROXY_ENABLED:
        return None

    if PROXY_USERNAME and PROXY_PASSWORD:
        return (PROXY_TYPE, PROXY_ADDR, PROXY_PORT, True, PROXY_USERNAME, PROXY_PASSWORD)
    else:
        return (PROXY_TYPE, PROXY_ADDR, PROXY_PORT)
