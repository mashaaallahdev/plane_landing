import asyncio
import os
import sys
import logging
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram import Bot

load_dotenv(".env")

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.quran_service import QuranService
from src.video_source import VideoSourceProvider
from src.video_composer import VideoComposer
from src.caption_generator import CaptionGenerator
from src.telegram_bot import PlaneQuranBot

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("generate_90s")

async def main():
    logger.info("==================================================")
    logger.info("Initiating 90-Second Quran Reel Generation Pipeline")
    logger.info("==================================================")

    qs = QuranService()
    vs = VideoSourceProvider()
    composer = VideoComposer()
    cap_gen = CaptionGenerator()
    bot_service = PlaneQuranBot()

    # 1. Select 90-second Ayah sequence from Surah Ar-Rahman (Ayahs 1 to 16)
    logger.info("Selecting Surah Ar-Rahman (Ayahs 1-16) for ~89s duration...")
    q_data = qs.select_ayah_sequence(
        surah_number=55,
        start_ayah=1,
        min_sec=85.0,
        max_sec=90.0,
    )
    total_dur = q_data["total_duration"]
    logger.info(f"Selected Surah: {q_data['surah_name_en']} ({q_data['surah_name_ar']})")
    logger.info(f"Ayah Range: {q_data['start_ayah']} - {q_data['end_ayah']} ({len(q_data['ayahs'])} ayahs)")
    logger.info(f"Exact Audio Duration: {total_dur:.2f} seconds")

    # 2. Pick long commercial jet landing video
    hkia_video = Path("assets/videos/cache/landing_hkia.webm")
    if hkia_video.exists():
        video_path = hkia_video
    else:
        video_path = vs.get_airplane_video()
    logger.info(f"Using Aviation Video: {video_path.name}")

    # 3. Compose the vertical 9:16 reel with glass header, floating harkat verses, and bottom-left watermark
    logger.info(f"Composing 90s Reel ({total_dur:.2f}s) at 1080x1920 @ 30 FPS...")
    output_mp4 = composer.compose_reel(video_path, q_data)
    logger.info(f"Video Reel successfully created: {output_mp4} ({output_mp4.stat().st_size / (1024*1024):.2f} MB)")

    # 4. Generate beautiful caption
    caption = cap_gen.generate_caption(q_data)
    logger.info(f"Generated Caption Preview:\n{caption}\n")

    # 5. Dispatch to Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        logger.info(f"Dispatching 90s Reel to Telegram chat {TELEGRAM_CHAT_ID}...")
        tg_bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot_service.send_reel_to_chat(
            bot=tg_bot,
            chat_id=TELEGRAM_CHAT_ID,
            video_path=output_mp4,
            caption=caption,
            duration=int(total_dur),
        )
        logger.info("🎉 90-Second Reel successfully delivered to Telegram!")
    else:
        logger.warning("Telegram credentials not configured; skipped dispatch.")

if __name__ == "__main__":
    asyncio.run(main())
