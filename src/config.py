import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")

# Telegram Settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Video Settings
MIN_DURATION_SECONDS = int(os.getenv("MIN_DURATION_SECONDS", "15"))
MAX_DURATION_SECONDS = int(os.getenv("MAX_DURATION_SECONDS", "90"))
DAILY_GENERATION_COUNT = int(os.getenv("DAILY_GENERATION_COUNT", "10"))
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))

# Reciter
QURAN_RECITER_ID = os.getenv("QURAN_RECITER_ID", "Yasser_Ad-Dussary_128kbps").strip()
RECITER_NAME_EN = "Sheikh Yasir Al-Dosari"
RECITER_NAME_AR = "الشيخ ياسر الدوسري"

# Branding / Tag
CHANNEL_TAG = os.getenv("CHANNEL_TAG", "@QuranInTheSky").strip()

# Video Stock APIs
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "").strip()

# Server Settings (for Render)
PORT = int(os.getenv("PORT", "8080"))
HOST = os.getenv("HOST", "0.0.0.0")

# Directories
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
VIDEOS_DIR = ASSETS_DIR / "videos"
VIDEO_CACHE_DIR = VIDEOS_DIR / "cache"
DATA_DIR = BASE_DIR / "data"
QURAN_CACHE_DIR = DATA_DIR / "quran_cache"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure all directories exist
for d in [FONTS_DIR, VIDEOS_DIR, VIDEO_CACHE_DIR, DATA_DIR, QURAN_CACHE_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Font paths
ARABIC_FONT_PATH = FONTS_DIR / "Amiri-Bold.ttf"
ENGLISH_FONT_PATH = FONTS_DIR / "Inter-Bold.ttf"
