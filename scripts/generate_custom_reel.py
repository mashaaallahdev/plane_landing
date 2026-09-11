import os
import sys
import argparse
import asyncio
import logging
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
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
logger = logging.getLogger("custom_reel")

def main():
    parser = argparse.ArgumentParser(
        description="Generate a Custom Airplane Quran Reel for any Surah and exact verse range."
    )
    parser.add_argument(
        "--surah",
        type=str,
        default=None,
        help="Surah number (1-114) or name (e.g. 67, Mulk, Rahman, Baqarah)",
    )
    parser.add_argument(
        "--start",
        "--start-ayah",
        dest="start_ayah",
        type=int,
        default=None,
        help="Starting Ayah number (e.g. 1)",
    )
    parser.add_argument(
        "--end",
        "--end-ayah",
        dest="end_ayah",
        type=int,
        default=None,
        help="Ending Ayah number for exact range (e.g. 5 or 16)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Dispatch the generated reel to Telegram automatically",
    )

    args = parser.parse_args()

    bot_service = PlaneQuranBot()
    qs = bot_service.quran_service

    surah_num = None
    start_ayah = args.start_ayah
    end_ayah = args.end_ayah
    send_to_telegram = args.send

    # If no surah provided, enter interactive friendly prompt
    if not args.surah and args.start_ayah is None and args.end_ayah is None:
        print("\n" + "=" * 62)
        print("✈️   CUSTOM AIRPLANE QURAN REEL GENERATOR")
        print("=" * 62)
        print("Reciter: Sheikh Yasir Ad-Dosary | 100% Halal Aviation Footage\n")

        # 1. Surah selection
        while True:
            surah_in = input("📖 Enter Surah Number (1-114) or Name (e.g. 67, Mulk, Rahman) [Enter for Random]: ").strip()
            if not surah_in:
                print("🎲 Selecting random Surah...")
                break
            surah_info = qs.find_surah(surah_in)
            if surah_info:
                surah_num = surah_info["number"]
                print(f"✅ Selected: Surah {surah_num} - {surah_info['englishName']} ({surah_info['name']})")
                print(f"   Total Ayahs: {surah_info['numberOfAyahs']} | Type: {surah_info['revelationType']}\n")
                break
            else:
                print(f"❌ Surah matching '{surah_in}' not found. Please try again.")

        # 2. Verse selection
        if surah_num:
            surah_info = qs.get_surah_info(surah_num)
            max_ayah = surah_info["numberOfAyahs"]
            while True:
                start_in = input(f"📍 Starting Ayah (1 to {max_ayah}) [Enter for default]: ").strip()
                if not start_in:
                    break
                if start_in.isdigit() and 1 <= int(start_in) <= max_ayah:
                    start_ayah = int(start_in)
                    break
                print(f"❌ Must be between 1 and {max_ayah}.")

            if start_ayah is not None:
                while True:
                    end_in = input(f"📍 Ending Ayah ({start_ayah} to {max_ayah}) [Enter for auto duration]: ").strip()
                    if not end_in:
                        break
                    if end_in.isdigit() and start_ayah <= int(end_in) <= max_ayah:
                        end_ayah = int(end_in)
                        break
                    print(f"❌ Must be between {start_ayah} and {max_ayah}.")

        # 3. Telegram confirmation
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            tg_in = input("\n📤 Send directly to Telegram chat? (Y/n) [Y]: ").strip().lower()
            send_to_telegram = tg_in != "n"
    else:
        if args.surah:
            info = qs.find_surah(args.surah)
            if info:
                surah_num = info["number"]
            elif args.surah.isdigit():
                surah_num = int(args.surah)
            else:
                print(f"❌ Surah matching '{args.surah}' not found.")
                sys.exit(1)

    range_desc = f"Ayahs {start_ayah}-{end_ayah}" if end_ayah else f"Ayah {start_ayah or 'Auto'}"
    print(f"\n🎬 Starting generation: Surah {surah_num or 'Random'} ({range_desc})...")

    video_path, caption, q_data = bot_service.generate_single_reel(
        surah_number=surah_num,
        start_ayah=start_ayah,
        end_ayah=end_ayah,
    )

    size_mb = video_path.stat().st_size / (1024 * 1024)
    print("\n" + "=" * 62)
    print("🎉 REEL GENERATION COMPLETE!")
    print("=" * 62)
    print(f"• Video File: {video_path}")
    print(f"• File Size:  {size_mb:.2f} MB")
    print(f"• Duration:   {q_data['total_duration']:.2f} seconds")
    print(f"• Surah:      {q_data['surah_name_en']} ({q_data['surah_name_ar']})")
    print(f"• Ayahs:      {q_data['start_ayah']} to {q_data['end_ayah']} ({len(q_data['ayahs'])} total)")
    print("=" * 62)
    print("\n--- Generated Caption Preview ---\n")
    print(caption)
    print("\n" + "=" * 62)

    if send_to_telegram:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("❌ Cannot send to Telegram: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing in .env")
            return
        print(f"📤 Dispatching to Telegram chat {TELEGRAM_CHAT_ID}...")
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
        print("✅ Reel delivered to Telegram successfully!")

if __name__ == "__main__":
    main()
