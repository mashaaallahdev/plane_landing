import asyncio
import logging
import random
from pathlib import Path
from typing import Optional
from datetime import datetime

from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
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
        end_ayah: Optional[int] = None,
        min_sec: float = MIN_DURATION_SECONDS,
        max_sec: float = MAX_DURATION_SECONDS,
    ) -> tuple[Path, str, dict]:
        """
        Generates a 9:16 vertical video reel with Sheikh Yasir Ad-Dosary's recitation
        and royalty-free airplane landing/takeoff video.
        Supports explicit Surah and Ayah range [start_ayah, end_ayah].
        Returns (video_path, formatted_caption, quran_data).
        """
        range_str = f"Ayahs {start_ayah}-{end_ayah}" if end_ayah else f"Ayah {start_ayah or 'Auto'}"
        logger.info(f"Initiating Reel generation (Surah: {surah_number or 'Random'}, {range_str})")
        
        # 1. Fetch Quran audio segment and metadata
        quran_data = self.quran_service.select_ayah_sequence(
            surah_number=surah_number,
            start_ayah=start_ayah,
            end_ayah=end_ayah,
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
            loop = asyncio.get_running_loop()
            video_path, caption, q_data = await loop.run_in_executor(
                None, self.generate_single_reel
            )
            await self.send_reel_to_chat(
                bot=bot,
                chat_id=TELEGRAM_CHAT_ID,
                video_path=video_path,
                caption=caption,
                duration=int(q_data["total_duration"]),
            )
        except Exception as e:
            logger.error(f"Error during scheduled reel generation: {e}", exc_info=True)

    async def post_init(self, application: Application):
        """Hook called by python-telegram-bot after the application is initialized and event loop is running."""
        logger.info("Bot application initialized. Setting up daily scheduler...")
        self.setup_daily_schedule(application.bot)

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
        try:
            if not self.scheduler.running:
                self.scheduler.start()
        except Exception as e:
            logger.warning(f"Could not start scheduler immediately (will start when loop runs): {e}")
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
            f"• `/generate` — Create a fresh random Reel\n"
            f"• `/generate <surah>` — Generate for a specific Surah by number or name (e.g. `/generate 67` or `/generate mulk`)\n"
            f"• `/generate <surah> <start_ayah> <end_ayah>` — Generate an exact verse range! (e.g. `/generate 67 1 5` or `/generate mulk 1 5`)\n"
            f"• `/surahs [query]` — Browse all Surahs, ayah counts, or search by name (e.g. `/surahs` or `/surahs rahman`)\n"
            f"• `/daily_batch` — Run batch generation on demand\n"
            f"• `/status` — Bot health and generation stats\n"
            f"• `/help` — Detailed usage instructions\n"
        )
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "🛠️ *Bot Commands & Exact Verse Range Usage:*\n\n"
            "• `/generate`:\n"
            "Generates a random Surah reel with clean airplane landing/takeoff footage.\n\n"
            "• `/generate <surah>`:\n"
            "Generates for a specific Surah by number or name (e.g. `/generate 67` or `/generate mulk`).\n\n"
            "• `/generate <surah> <start_ayah>`:\n"
            "Generates starting from a specific Ayah (e.g. `/generate 2 255` for Ayat Al-Kursi).\n\n"
            "• `/generate <surah> <start_ayah> <end_ayah>`:\n"
            "Generates an **exact verse range**! Examples:\n"
            "  - `/generate 67 1 5` (Surah Al-Mulk, Ayahs 1 to 5)\n"
            "  - `/generate mulk 1 5` (Lookup by Surah name!)\n"
            "  - `/generate 55 1 16` (Surah Ar-Rahman, Ayahs 1 to 16)\n"
            "  - `/generate 114 1 6` (Surah An-Naas, full Surah)\n"
            "  - `/generate 67:1-5` or `/generate 67 1-5` also supported!\n\n"
            "• `/surahs [query]`:\n"
            "Browse popular Surahs and verse counts, or search by name/number (e.g. `/surahs kahf`).\n\n"
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

    async def cmd_surahs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Browse or search Surahs with their numbers and total verse counts."""
        query = " ".join(context.args).strip() if context.args else ""
        if query:
            results = self.quran_service.search_surahs(query)[:8]
            if not results:
                await update.message.reply_text(f"🔍 No Surahs found matching '{query}'. Try typing a number (1-114) or name (e.g. Mulk, Rahman).")
                return
            lines = [f"📖 *Matching Surahs for '{query}':*\n"]
            for s in results:
                lines.append(f"• **{s['number']}. {s['englishName']}** ({s['name']}) — {s['numberOfAyahs']} Ayahs")
                lines.append(f"  👉 `/generate {s['number']} 1 {min(s['numberOfAyahs'], 5)}`\n")
            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
        else:
            featured = [
                (1, "Al-Faatiha", 7),
                (36, "Yaseen", 83),
                (55, "Ar-Rahmaan", 78),
                (56, "Al-Waqi'a", 96),
                (67, "Al-Mulk", 30),
                (112, "Al-Ikhlaas", 4),
                (113, "Al-Falaq", 5),
                (114, "An-Naas", 6),
            ]
            lines = [
                "📖 *Quran Surahs & Verse Range Guide:*\n",
                "You can generate ANY Surah (1-114) and ANY exact verse range!\n",
                "*Examples:*",
                "• `/generate 67 1 5` (Surah Al-Mulk, Ayahs 1 to 5)",
                "• `/generate 55 1 16` (Surah Ar-Rahman, Ayahs 1 to 16)",
                "• `/generate mulk 1 5` (Lookup by name also works!)",
                "• `/generate 2 255 255` (Ayat Al-Kursi)\n",
                "*Search any Surah:*",
                "Type `/surahs <name>` (e.g. `/surahs kahf` or `/surahs 18`)\n",
                "*Popular Surahs:*",
            ]
            for num, name, ayahs in featured:
                lines.append(f"• **{num}. {name}** ({ayahs} Ayahs) ➔ `/generate {num} 1 {min(ayahs, 5)}`")
            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    async def cmd_generate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /generate and /generate <surah> [start_ayah] [end_ayah] for instant on-demand creation."""
        user_info = f"{update.effective_user.first_name} (ID: {update.effective_user.id})" if update.effective_user else "unknown"
        logger.info(f"cmd_generate invoked by {user_info} with args={context.args}")
        # Parse optional arguments
        surah_info = None
        surah_num = None
        start_ayah = None
        end_ayah = None

        if context.args:
            raw_arg = " ".join(context.args).strip()
            # Format: "67:1-5" or "mulk:1-5"
            if ":" in raw_arg:
                try:
                    parts = raw_arg.split(":")
                    surah_token = parts[0].strip()
                    surah_info = self.quran_service.find_surah(surah_token)
                    if surah_info:
                        surah_num = surah_info["number"]
                    else:
                        surah_num = int(surah_token)
                    range_part = parts[1].strip()
                    if "-" in range_part:
                        start_ayah = int(range_part.split("-")[0].strip())
                        end_ayah = int(range_part.split("-")[1].strip())
                    else:
                        start_ayah = int(range_part)
                except Exception:
                    pass
            elif len(context.args) == 2 and "-" in context.args[1]:
                try:
                    surah_token = context.args[0]
                    surah_info = self.quran_service.find_surah(surah_token)
                    surah_num = surah_info["number"] if surah_info else int(surah_token)
                    start_ayah = int(context.args[1].split("-")[0].strip())
                    end_ayah = int(context.args[1].split("-")[1].strip())
                except Exception:
                    pass
            else:
                try:
                    if len(context.args) >= 1:
                        surah_token = context.args[0]
                        surah_info = self.quran_service.find_surah(surah_token)
                        surah_num = surah_info["number"] if surah_info else int(surah_token)
                    if len(context.args) >= 2:
                        start_ayah = int(context.args[1])
                    if len(context.args) >= 3:
                        end_ayah = int(context.args[2])
                except Exception:
                    pass

        if surah_num is not None:
            if surah_num < 1 or surah_num > 114:
                await update.message.reply_text("❌ Invalid Surah number. Please choose between 1 and 114. Use `/surahs` to browse.")
                return
            surah_info = self.quran_service.get_surah_info(surah_num)

        if surah_info and start_ayah is not None:
            max_ayah = surah_info["numberOfAyahs"]
            if start_ayah > max_ayah:
                await update.message.reply_text(f"❌ Surah {surah_info['englishName']} only has {max_ayah} Ayahs. Starting Ayah cannot be {start_ayah}.")
                return
            if end_ayah is not None and end_ayah > max_ayah:
                end_ayah = max_ayah

        if start_ayah is not None and end_ayah is not None and start_ayah > end_ayah:
            await update.message.reply_text("❌ Invalid range: Starting Ayah must be less than or equal to Ending Ayah.")
            return

        range_desc = f"Ayahs {start_ayah}-{end_ayah}" if end_ayah else (f"Ayah {start_ayah}" if start_ayah else "Auto Ayahs")
        surah_desc = f"Surah {surah_info['englishName']} ({surah_info['name']})" if surah_info else (f"Surah {surah_num}" if surah_num else "Random Surah")

        msg = await update.message.reply_text(
            f"⏳ *Generating your 9:16 Airplane Quran Reel...*\n"
            f"• Target: {surah_desc} ({range_desc})\n"
            f"• Reciter: {RECITER_NAME_EN}\n"
            "• Fetching Arabic calligraphy with Harkat & aviation footage...\n"
            "Please wait 30-90 seconds while your high-definition video is rendered! ✈️✨",
            parse_mode=ParseMode.MARKDOWN,
        )

        try:
            # Run blocking video generation in background thread pool to avoid blocking asyncio event loop
            loop = asyncio.get_running_loop()
            video_path, caption, q_data = await loop.run_in_executor(
                None,
                self.generate_single_reel,
                surah_num,
                start_ayah,
                end_ayah,
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

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle plain text messages so users can type commands without a leading slash (e.g. 'generate 2 1 7')."""
        if not update.message or not update.message.text:
            return
        raw_text = update.message.text.strip()
        user_info = f"{update.effective_user.first_name} (ID: {update.effective_user.id})" if update.effective_user else "unknown"
        logger.info(f"Received text message from {user_info}: '{raw_text}'")

        cleaned = raw_text.lstrip("/!").strip()
        lower = cleaned.lower()

        if lower.startswith("generate"):
            parts = cleaned.split()[1:]
            context.args = parts
            await self.cmd_generate(update, context)
        elif lower.startswith("surah") or lower.startswith("list"):
            parts = cleaned.split()[1:]
            context.args = parts
            await self.cmd_surahs(update, context)
        elif lower == "status":
            await self.cmd_status(update, context)
        elif lower in ("help", "start"):
            await self.cmd_start(update, context)
        elif lower.startswith("daily_batch"):
            await self.cmd_daily_batch(update, context)
        else:
            name = update.effective_user.first_name if update.effective_user else "Friend"
            help_msg = (
                f"السلام عليكم *{name}*! ✈️📖\n\n"
                "To generate a 9:16 vertical Reel, send:\n"
                "• `/generate` — Create random Reel\n"
                "• `/generate 2 1 5` — Surah Al-Baqara, Ayahs 1 to 5\n"
                "• `/generate 67 1 5` — Surah Al-Mulk, Ayahs 1 to 5\n"
                "• `/surahs` — Search & browse all 114 Surahs\n"
                "• `/status` — View bot uptime & stats"
            )
            await update.message.reply_text(help_msg, parse_mode=ParseMode.MARKDOWN)

    def build_app(self) -> Application:
        """Builds and configures the Telegram Application instance."""
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set. Please set it in your .env or environment.")

        logger.info("Initializing Telegram Bot Application...")
        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(self.post_init).build()

        # Register command handlers (e.g. /generate, /start)
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(CommandHandler("generate", self.cmd_generate))
        app.add_handler(CommandHandler("surahs", self.cmd_surahs))
        app.add_handler(CommandHandler("list", self.cmd_surahs))
        app.add_handler(CommandHandler("daily_batch", self.cmd_daily_batch))

        # Register plain text handler (e.g. "generate 2 1 7", "status", "surahs")
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_text_message))

        return app

    def run(self):
        """Starts the Telegram bot application with polling and scheduler (standalone mode)."""
        app = self.build_app()
        logger.info("Starting bot polling loop...")
        app.run_polling(drop_pending_updates=False)

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    bot_service = PlaneQuranBot()
    bot_service.run()
