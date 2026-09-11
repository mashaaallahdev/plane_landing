import os
import requests
import logging
from pathlib import Path
from src.config import ARABIC_FONT_PATH, ENGLISH_FONT_PATH, FONTS_DIR

logger = logging.getLogger(__name__)

AMIRI_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Bold.ttf"
ROBOTO_URL = "https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf"

def ensure_fonts():
    """Ensure Arabic and English fonts are downloaded and accessible."""
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download Arabic Font (Amiri Bold)
    if not ARABIC_FONT_PATH.exists() or ARABIC_FONT_PATH.stat().st_size < 1000:
        logger.info(f"Downloading Arabic font to {ARABIC_FONT_PATH}...")
        try:
            r = requests.get(AMIRI_URL, timeout=20)
            if r.ok:
                with open(ARABIC_FONT_PATH, "wb") as f:
                    f.write(r.content)
                logger.info("Amiri-Bold.ttf downloaded successfully.")
            else:
                logger.warning(f"Failed to download Arabic font from {AMIRI_URL}: HTTP {r.status_code}")
        except Exception as e:
            logger.error(f"Error downloading Arabic font: {e}")

    # Download English Font (Roboto/Inter Bold)
    if not ENGLISH_FONT_PATH.exists() or ENGLISH_FONT_PATH.stat().st_size < 1000:
        logger.info(f"Downloading English font to {ENGLISH_FONT_PATH}...")
        try:
            r = requests.get(ROBOTO_URL, timeout=20)
            if r.ok:
                with open(ENGLISH_FONT_PATH, "wb") as f:
                    f.write(r.content)
                logger.info("Inter/Roboto font downloaded successfully.")
            else:
                logger.warning(f"Failed to download English font from {ROBOTO_URL}: HTTP {r.status_code}")
        except Exception as e:
            logger.error(f"Error downloading English font: {e}")

    return ARABIC_FONT_PATH.exists() and ENGLISH_FONT_PATH.exists()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = ensure_fonts()
    print("Fonts ready:", success)
