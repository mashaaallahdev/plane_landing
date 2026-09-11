import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv(".env")
token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

async def send_test_video():
    if not token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing in .env")
        return

    bot = Bot(token=token)
    
    # Pick the best available generated video in output/
    output_dir = Path("output")
    videos = sorted(output_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not videos:
        print("Error: No video found in output/ directory!")
        return

    video_path = videos[0]
    print(f"Selected video: {video_path.name} ({video_path.stat().st_size / (1024*1024):.2f} MB)")

    caption = (
        "🤍 *In the calm expanse of the skies, let your burdens depart and divine peace touch down softly.*\n\n"
        "📖 **Surah Al-Falaq** (سُورَةُ الفَلَقِ)\n"
        "📍 **Ayahs 1-5**\n"
        "🎙️ **Reciter:** Sheikh Yasir Al-Dosari (الشيخ ياسر الدوسري)\n\n"
        "📜 **Translation (Sahih International):**\n"
        '"Say, I seek refuge in the Lord of daybreak From the evil of that which He created And from the evil of darkness when it settles And from the evil of the blowers in knots And from the evil of an envier when he envies."\n\n'
        "#Quran #YasirAlDosari #QuranRecitation #AirplaneLanding #AirplaneDeparture #Aviation #Flight #FacebookReels #IslamicReels #Peace #QuranTilawat #Islam #Shorts"
    )

    print(f"Uploading and dispatching to Telegram chat ID: {chat_id}...")
    with open(video_path, "rb") as f:
        msg = await bot.send_video(
            chat_id=chat_id,
            video=f,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            supports_streaming=True,
            width=1080,
            height=1920,
            duration=20,
            write_timeout=180,
            read_timeout=180,
        )

    print(f"✅ Video successfully sent to Telegram! Message ID: {msg.message_id}")

if __name__ == "__main__":
    asyncio.run(send_test_video())
