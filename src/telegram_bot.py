import asyncio
import logging
import random
from pathlib import Path
from typing import Optional
from datetime import datetime

from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    DAILY_GENERATION_COUNT,
    RECITER_NAME_EN,
    RECITER_NAME_AR,
    MIN_DURATION_SECONDS,
    MAX_DURATION_SECONDS,
)
from src.quran_service import QuranService
from src.video_source import VideoSourceProvider
from src.video_composer import VideoComposer
from src.caption_generator import CaptionGenerator

logger = logging.getLogger(__name__)

class PlaneQuranBot:
    def __init__(self):
        self.quran_service = QuranService()
        self.video_source = VideoSourceProvider()
        self.composer = VideoComposer()
        self.caption_gen = CaptionGenerator()
        self.scheduler = AsyncIOScheduler()
        self.total_generated = 0
        self.start_time = datetime.now()

    def generate_single_reel(
        self,
        surah_number: Optional[int] = None,
        start_ayah: Optional[int] = None,
        min_sec: float = MIN_DURATION_SECONDS,
        max_sec: float = MAX_DURATION_SECONDS,
    ) -> tuple[Path, str, dict]:
        """
        Generates a 9:16 vertical video reel with Sheikh Yasir Ad-Dosary's recitation
        and royalty-free airplane landing/takeoff video.
        Returns (video_path, formatted_caption, quran_data).
        """
        logger.info(f"Initiating Reel generation (Surah: {surah_number or 'Random'}, Ayah: {start_ayah or 'Auto'})")
        
        # 1. Fetch Quran audio segment and metadata
        quran_data = self.quran_service.select_ayah_sequence(
            surah_number=surah_number,
            start_ayah=start_ayah,
            min_sec=min_sec,
            max_sec=max_sec,
        )

        # 2. Get airplane footage
        video_path = self.video_source.get_airplane_video()

        # 3. Compose the vertical reel
        output_mp4 = self.composer.compose_reel(video_path, quran_data)

        # 4. Generate the spiritual one-liner caption
        caption = self.caption_gen.generate_caption(quran_data)

        self.total_generated += 1
        return output_mp4, caption, quran_data

    async def send_reel_to_chat(
        self,
        bot: Bot,
        chat_id: str | int,
        video_path: Path,
        caption: str,
        duration: int = 30,
    ):
        """Sends the generated MP4 file to a Telegram chat/channel as a vertical video."""
        logger.info(f"Dispatching Reel {video_path.name} to chat {chat_id}...")
        with open(video_path, "rb") as v_file:
            await bot.send_video(
                chat_id=chat_id,
                video=v_file,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                supports_streaming=True,
                width=1080,
                height=1920,
                duration=duration,
                write_timeout=120,
                read_timeout=120,
            )
        logger.info("Reel successfully delivered to Telegram!")

    async def scheduled_job(self, bot: Bot):
        """Job triggered by APScheduler for daily 10x automation."""
        if not TELEGRAM_CHAT_ID:
            logger.warning("TELEGRAM_CHAT_ID not configured. Skipping scheduled delivery.")
            return

        logger.info("Executing scheduled Reel generation job...")
        try:
            video_path, caption, q_data = self.generate_single_reel()
            await self.send_reel_to_chat(
                bot=bot,
                chat_id=TELEGRAM_CHAT_ID,
                video_path=video_path,
                caption=caption,
                duration=int(q_data["total_duration"]),
            )
        except Exception as e:
            logger.error(f"Error during scheduled reel generation: {e}", exc_info=True)

    def setup_daily_schedule(self, bot: Bot):
        """
        Schedules 10 automated generation jobs evenly distributed throughout the day.
        Interval = 24 / 10 = ~2.4 hours (every 144 minutes).
        """
        interval_minutes = 144
        # Schedule at 00:00, 02:24, 04:48, 07:12, 09:36, 12:00, 14:24, 16:48, 19:12, 21:36 UTC
        times = [
            (0, 0), (2, 24), (4, 48), (7, 12), (9, 36),
            (12, 0), (14, 24), (16, 48), (19, 12), (21, 36)
        ]
        for hour, minute in times:
            self.scheduler.add_job(
                self.scheduled_job,
                CronTrigger(hour=hour, minute=minute),
                args=[bot],
                name=f"daily_reel_{hour:02d}{minute:02d}",
                replace_existing=True,
            )
        self.scheduler.start()
        logger.info(f"Configured {len(times)} daily automated generation triggers.")

    # ---------------- Telegram Command Handlers ----------------

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user_name = update.effective_user.first_name if update.effective_user else "Friend"
        welcome_text = (
            f"السلام عليكم ورحمة الله وبركاته, *{user_name}*! ✈️📖\n\n"
            f"Welcome to the *Autonomous Airplane Quran Reels Bot*.\n\n"
            f"🎙️ **Reciter:** {RECITER_NAME_EN} ({RECITER_NAME_AR})\n"
            f"✈️ **Theme:** Halal, royalty-free commercial airplane landings & departures\n"
            f"📏 **Reels Length:** 15s to 90s (9:16 vertical HD 1080x1920)\n"
            f"⏰ **Automated Schedule:** 10x daily reels delivered autonomously\n\n"
            f"**Available Commands:**\n"
            f"• `/generate` - Instantly create and receive a new Reel\n"
            f"• `/generate <surah> [ayah]` - Generate for a specific Surah (1-114)\n"
            f"• `/daily_batch` - Run batch generation on demand\n"
            f"• `/status` - Bot health and generation stats\n"
            f"• `/help` - Usage instructions and details\n"
        )
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "🛠️ *Bot Commands & Usage:*\n\n"
            "• `/generate`:\n"
            "Generates a random Surah reel (15s to 90s) with clean airplane landing/takeoff video.\n\n"
            "• `/generate <surah_number>`:\n"
            "Generates a reel for the specified Surah number (e.g. `/generate 67` for Al-Mulk).\n\n"
            "• `/generate <surah_number> <start_ayah>`:\n"
            "Generates starting from a specific Ayah (e.g. `/generate 2 255` for Ayat Al-Kursi).\n\n"
            "• `/status`:\n"
            "Displays current bot uptime, generation counts, and storage status.\n"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        status_text = (
            "📊 *System & Bot Status:*\n\n"
            f"• **Status:** Active & Ready ✅\n"
            f"• **Uptime:** {hours}h {minutes}m {seconds}s\n"
            f"• **Reels Generated This Session:** {self.total_generated}\n"
            f"• **Reciter:** {RECITER_NAME_EN}\n"
            f"• **Surah Range:** 1 - 114\n"
            f"• **Duration Limits:** {MIN_DURATION_SECONDS}s - {MAX_DURATION_SECONDS}s\n"
            f"• **Target Chat ID:** `{TELEGRAM_CHAT_ID or 'Not configured'}`\n"
            f"• **Daily Schedule Count:** {DAILY_GENERATION_COUNT}x daily\n"
        )
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_generate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /generate and /generate <surah> [ayah] for instant on-demand creation."""
        msg = await update.message.reply_text(
            "⏳ *Generating your 9:16 Airplane Quran Reel...*\n"
            f"• Reciter: {RECITER_NAME_EN}\n"
            "• Fetching authentic Arabic calligraphy, translation & aviation footage...\n"
            "Please wait 30-60 seconds while your high-definition video is rendered! ✈️✨",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Parse optional arguments
        surah_num = None
        start_ayah = None
        if context.args:
            try:
                surah_num = int(context.args[0])
                if surah_num < 1 or surah_num > 114:
                    await msg.edit_text("❌ Invalid Surah number. Please choose between 1 and 114.")
                    return
            except ValueError:
                pass
            
            if len(context.args) > 1:
                try:
                    start_ayah = int(context.args[1])
                except ValueError:
                    pass

        try:
            # Run blocking video generation in background thread pool to avoid blocking asyncio event loop
            loop = asyncio.get_running_loop()
            video_path, caption, q_data = await loop.run_in_executor(
                None,
                self.generate_single_reel,
                surah_num,
                start_ayah,
                MIN_DURATION_SECONDS,
                MAX_DURATION_SECONDS,
            )

            await msg.edit_text("📤 *Uploading video reel to Telegram...*")
            await self.send_reel_to_chat(
                bot=context.bot,
                chat_id=update.effective_chat.id,
                video_path=video_path,
                caption=caption,
                duration=int(q_data["total_duration"]),
            )
            await msg.delete()

        except Exception as e:
            logger.error(f"Error generating on-demand reel: {e}", exc_info=True)
            await msg.edit_text(f"❌ Failed to generate video reel: `{e}`", parse_mode=ParseMode.MARKDOWN)

    async def cmd_daily_batch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Triggers batch generation of reels on-demand."""
        target_chat = TELEGRAM_CHAT_ID or update.effective_chat.id
        status_msg = await update.message.reply_text(
            f"🚀 *Starting batch generation of {DAILY_GENERATION_COUNT} Reels...*\n"
            f"Target: `{target_chat}`",
            parse_mode=ParseMode.MARKDOWN
        )

        success_count = 0
        loop = asyncio.get_running_loop()

        for i in range(1, DAILY_GENERATION_COUNT + 1):
            try:
                await status_msg.edit_text(
                    f"🎬 *Batch Progress:* Generating Reel {i}/{DAILY_GENERATION_COUNT}...\n"
                    f"Reciter: {RECITER_NAME_EN}"
                )
                video_path, caption, q_data = await loop.run_in_executor(
                    None,
                    self.generate_single_reel,
                    None, None, MIN_DURATION_SECONDS, MAX_DURATION_SECONDS
                )
                await self.send_reel_to_chat(
                    bot=context.bot,
                    chat_id=target_chat,
                    video_path=video_path,
                    caption=caption,
                    duration=int(q_data["total_duration"]),
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed Reel {i} in batch: {e}")

        await status_msg.edit_text(
            f"✅ *Batch generation completed!*\n"
            f"Successfully produced and sent {success_count}/{DAILY_GENERATION_COUNT} Reels."
        )

    def run(self):
        """Starts the Telegram bot application with polling and scheduler."""
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set. Please set it in your .env or environment.")

        logger.info("Initializing Telegram Bot Application...")
        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

        # Register handlers
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(CommandHandler("generate", self.cmd_generate))
        app.add_handler(CommandHandler("daily_batch", self.cmd_daily_batch))

        # Start daily 10x scheduler
        self.setup_daily_schedule(app.bot)

        logger.info("Starting bot polling loop...")
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    bot_service = PlaneQuranBot()
    bot_service.run()
