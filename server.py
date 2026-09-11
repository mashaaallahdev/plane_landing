import os
import sys
import asyncio
import logging
from datetime import datetime
from aiohttp import web

# Fix Windows console utf-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config import PORT, HOST, TELEGRAM_BOT_TOKEN
from src.telegram_bot import PlaneQuranBot

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("server")

bot_instance = None

async def handle_root(request):
    """Root endpoint for status information."""
    return web.json_response({
        "service": "Autonomous Airplane Landing/Departing Quran Reels Bot",
        "reciter": "Sheikh Yasir Al-Dosari",
        "format": "9:16 Vertical Reels (1080x1920)",
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
    })

async def handle_healthz(request):
    """Health check endpoint required for Render deployment."""
    return web.json_response({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    })

async def handle_status(request):
    """Detailed runtime status endpoint."""
    return web.json_response({
        "status": "running",
        "bot_configured": bool(TELEGRAM_BOT_TOKEN),
        "total_generated": getattr(bot_instance, "total_generated", 0) if bot_instance else 0,
        "uptime": str(datetime.now() - bot_instance.start_time) if bot_instance else "0",
    })

async def start_background_bot(app):
    """Background task to start the Telegram bot when the web server begins."""
    global bot_instance
    if TELEGRAM_BOT_TOKEN:
        logger.info("Starting Telegram Bot & Scheduler background worker...")
        bot_instance = PlaneQuranBot()
        loop = asyncio.get_running_loop()
        # Run Telegram Bot in executor thread so it doesn't block the web server
        app["bot_task"] = loop.run_in_executor(None, bot_instance.run)
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not provided. Bot worker will not start.")

async def cleanup_background_bot(app):
    """Cleanup when server stops."""
    logger.info("Stopping web server and background bot worker...")

def create_app():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/healthz", handle_healthz)
    app.router.add_get("/status", handle_status)
    app.on_startup.append(start_background_bot)
    app.on_cleanup.append(cleanup_background_bot)
    return app

if __name__ == "__main__":
    logger.info(f"Starting aiohttp web server on {HOST}:{PORT}")
    app = create_app()
    web.run_app(app, host=HOST, port=PORT)
