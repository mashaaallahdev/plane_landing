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

# Fix for Pillow 10+ where Image.ANTIALIAS was removed for MoviePy
try:
    from PIL import Image
    if not hasattr(Image, "ANTIALIAS"):
        Image.ANTIALIAS = getattr(Image, "Resampling", Image).LANCZOS
except ImportError:
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

def run_interactive():
    """Interactive wizard to choose Surah and exact verse range."""
    bot_service = PlaneQuranBot()
    qs = bot_service.quran_service

    print("\n" + "=" * 60)
    print("✈️  Autonomous Airplane Quran Reel Generator (Interactive Mode)")
    print("=" * 60)
    print("Reciter: Sheikh Yasir Ad-Dosary | Halal Commercial Aviation Footage\n")

    # 1. Surah selection
    surah_num = None
    surah_info = None
    while True:
        surah_input = input("📖 Enter Surah Number (1-114) or Name (e.g. 67, Mulk, Rahman) [Enter for Random]: ").strip()
        if not surah_input:
            print("🎲 Random Surah will be selected.")
            break
        surah_info = qs.find_surah(surah_input)
        if surah_info:
            surah_num = surah_info["number"]
            print(f"✅ Selected: Surah {surah_num} - {surah_info['englishName']} ({surah_info['name']})")
            print(f"   Total Ayahs: {surah_info['numberOfAyahs']} | Revelation: {surah_info['revelationType']}")
            break
        else:
            print(f"❌ Could not find Surah matching '{surah_input}'. Please try again.")

    # 2. Verse Range selection
    start_ayah = None
    end_ayah = None
    if surah_info:
        max_ayah = surah_info["numberOfAyahs"]
        while True:
            start_in = input(f"📍 Starting Ayah (1 to {max_ayah}) [Enter for Auto]: ").strip()
            if not start_in:
                break
            if start_in.isdigit() and 1 <= int(start_in) <= max_ayah:
                start_ayah = int(start_in)
                break
            print(f"❌ Please enter a valid Ayah between 1 and {max_ayah}.")

        if start_ayah is not None:
            while True:
                end_in = input(f"📍 Ending Ayah ({start_ayah} to {max_ayah}) [Enter for Auto duration]: ").strip()
                if not end_in:
                    break
                if end_in.isdigit() and start_ayah <= int(end_in) <= max_ayah:
                    end_ayah = int(end_in)
                    break
                print(f"❌ Ending Ayah must be between {start_ayah} and {max_ayah}.")

    # 3. Telegram dispatch option
    send_tg = False
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        tg_in = input("📤 Dispatch video to Telegram when generated? (Y/n) [Y]: ").strip().lower()
        send_tg = tg_in != "n"

    print("\n🎬 Generating your custom 9:16 vertical Reel, please wait...")
    video_path, caption, q_data = bot_service.generate_single_reel(
        surah_number=surah_num,
        start_ayah=start_ayah,
        end_ayah=end_ayah,
    )

    print(f"\n🎉 Reel generated successfully!")
    print(f"• Video: {video_path}")
    print(f"• Duration: {q_data['total_duration']:.2f}s")
    print(f"• Ayahs: {q_data['start_ayah']} - {q_data['end_ayah']}")
    print(f"\n--- Caption Preview ---\n{caption}\n")

    if send_tg:
        print(f"Dispatching to Telegram chat {TELEGRAM_CHAT_ID}...")
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
        print("✅ Delivered to Telegram successfully!")

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
        "-i",
        "--interactive",
        action="store_true",
        help="Run in interactive wizard mode to pick Surah and verse range easily",
    )
    parser.add_argument(
        "--surah",
        type=str,
        default=None,
        help="Surah number (1-114) or name (e.g. 67, Mulk, Rahman) for 'generate' mode",
    )
    parser.add_argument(
        "--start-ayah",
        "--ayah",
        dest="start_ayah",
        type=int,
        default=None,
        help="Starting Ayah number for 'generate' mode",
    )
    parser.add_argument(
        "--end-ayah",
        type=int,
        default=None,
        help="Ending Ayah number for exact verse range (e.g. --surah 67 --start-ayah 1 --end-ayah 5)",
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

    if args.interactive:
        run_interactive()
        return

    if args.mode == "bot":
        logger.info("Starting Autonomous Telegram Bot Service...")
        bot_service = PlaneQuranBot()
        bot_service.run()

    elif args.mode == "generate":
        bot_service = PlaneQuranBot()
        surah_num = None
        if args.surah:
            surah_info = bot_service.quran_service.find_surah(args.surah)
            if surah_info:
                surah_num = surah_info["number"]
            elif args.surah.isdigit():
                surah_num = int(args.surah)
            else:
                logger.error(f"Could not find Surah matching '{args.surah}'")
                sys.exit(1)

        range_str = f"Ayahs {args.start_ayah}-{args.end_ayah}" if args.end_ayah else f"Ayah {args.start_ayah or 'Auto'}"
        logger.info(f"Generating single reel (Surah: {surah_num or 'Random'}, {range_str})...")
        video_path, caption, q_data = bot_service.generate_single_reel(
            surah_number=surah_num,
            start_ayah=args.start_ayah,
            end_ayah=args.end_ayah,
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

