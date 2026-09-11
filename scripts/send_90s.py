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

async def send():
    bot = Bot(token=token)
    if len(sys.argv) > 1:
        video_path = Path(sys.argv[1])
    else:
        video_path = Path("output/reel_ar_rahmaan_90s_compressed.mp4")
        if not video_path.exists():
            mp4_files = sorted(Path("output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            if mp4_files:
                video_path = mp4_files[0]

    if not video_path.exists():
        print(f"Video file not found at {video_path}!")
        return

    caption = (
        "🤍 *In the calm expanse of the skies, let your burdens depart and divine peace touch down softly.*\n\n"
        "📖 **Surah Ar-Rahmaan** (سُورَةُ الرَّحۡمَٰن)\n"
        "📍 **Ayahs 1-16**\n"
        "🎙️ **Reciter:** Sheikh Yasir Al-Dosari (الشيخ ياسر الدوسري)\n"
        "⏱️ **Length:** 89s (Full 90-Second Reel)\n\n"
        "📜 **Translation (Sahih International):**\n"
        '"The Most Merciful Taught the Quran, Created man, [And] taught him eloquence. The sun and the moon [move] by precise calculation, And the stars and trees prostrate..."\n\n'
        "#Quran #YasirAlDosari #SurahRahman #Aviation #AirplaneLanding #FacebookReels #IslamicReels #Peace #Shorts"
    )

    print(f"Dispatching 90s Reel ({video_path.stat().st_size / (1024*1024):.2f} MB) to chat {chat_id}...")
    with open(video_path, "rb") as f:
        msg = await bot.send_video(
            chat_id=chat_id,
            video=f,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            supports_streaming=True,
            width=1080,
            height=1920,
            duration=89,
            write_timeout=240,
            read_timeout=240,
        )
    print(f"🎉 Successfully delivered 90s Reel! Message ID: {msg.message_id}")

if __name__ == "__main__":
    asyncio.run(send())
