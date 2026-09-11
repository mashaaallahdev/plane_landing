import argparse
import sys
import asyncio
import logging
from pathlib import Path

# Fix Windows console utf-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from telegram import Bot
from src.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    DAILY_GENERATION_COUNT,
    MIN_DURATION_SECONDS,
    MAX_DURATION_SECONDS,
)
from src.telegram_bot import PlaneQuranBot

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("main")

async def run_batch_generation(count: int, send_to_telegram: bool = False):
    """Generate a batch of reels (e.g. for GitHub Actions daily run or local generation)."""
    bot_service = PlaneQuranBot()
    logger.info(f"Starting batch generation of {count} reels (Send to Telegram: {send_to_telegram})...")

    tg_bot = None
    if send_to_telegram:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing. Cannot dispatch to Telegram.")
            sys.exit(1)
        tg_bot = Bot(token=TELEGRAM_BOT_TOKEN)

    success_count = 0
    for i in range(1, count + 1):
        logger.info(f"\n--- [Batch {i}/{count}] Generating Reel ---")
        try:
            video_path, caption, q_data = bot_service.generate_single_reel(
                min_sec=MIN_DURATION_SECONDS,
                max_sec=MAX_DURATION_SECONDS,
            )
            logger.info(f"Generated Reel #{i}: {video_path.name}")
            logger.info(f"Surah: {q_data['surah_name_en']} ({q_data['total_duration']:.1f}s)")

            if send_to_telegram and tg_bot:
                logger.info(f"Dispatching to Telegram chat {TELEGRAM_CHAT_ID}...")
                await bot_service.send_reel_to_chat(
                    bot=tg_bot,
                    chat_id=TELEGRAM_CHAT_ID,
                    video_path=video_path,
                    caption=caption,
                    duration=int(q_data["total_duration"]),
                )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to generate/send Reel #{i}: {e}", exc_info=True)

    logger.info(f"\n=======================================================")
    logger.info(f"Batch completed: {success_count}/{count} Reels successfully created!")
    logger.info(f"=======================================================")

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Airplane Landing/Departing Quran Reels Generator"
    )
    parser.add_argument(
        "--mode",
        choices=["bot", "generate", "batch"],
        default="bot",
        help="Execution mode: 'bot' (runs Telegram bot with scheduler), 'generate' (single reel), 'batch' (multi-reel generation)",
    )
    parser.add_argument(
        "--surah",
        type=int,
        default=None,
        help="Surah number (1-114) for 'generate' mode",
    )
    parser.add_argument(
        "--ayah",
        type=int,
        default=None,
        help="Starting Ayah number for 'generate' mode",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DAILY_GENERATION_COUNT,
        help="Number of reels to generate in 'batch' mode (default 10)",
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Automatically send generated reels to Telegram in 'batch' or 'generate' mode",
    )

    args = parser.parse_args()

    if args.mode == "bot":
        logger.info("Starting Autonomous Telegram Bot Service...")
        bot_service = PlaneQuranBot()
        bot_service.run()

    elif args.mode == "generate":
        bot_service = PlaneQuranBot()
        logger.info(f"Generating single reel (Surah: {args.surah or 'Random'}, Ayah: {args.ayah or 'Auto'})...")
        video_path, caption, q_data = bot_service.generate_single_reel(
            surah_number=args.surah,
            start_ayah=args.ayah,
        )
        logger.info(f"\nGenerated Video: {video_path}")
        logger.info(f"Duration: {q_data['total_duration']:.2f}s")
        logger.info(f"\n--- Caption Preview ---\n{caption}\n")

        if args.send_telegram:
            if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
                logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
                sys.exit(1)
            tg_bot = Bot(token=TELEGRAM_BOT_TOKEN)
            asyncio.run(
                bot_service.send_reel_to_chat(
                    bot=tg_bot,
                    chat_id=TELEGRAM_CHAT_ID,
                    video_path=video_path,
                    caption=caption,
                    duration=int(q_data["total_duration"]),
                )
            )

    elif args.mode == "batch":
        asyncio.run(run_batch_generation(count=args.count, send_to_telegram=args.send_telegram))

if __name__ == "__main__":
    main()
