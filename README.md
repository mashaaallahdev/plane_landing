# ✈️ Autonomous Airplane Landing/Departing Quran Reels Engine

An autonomous, 100% halal video generation engine and interactive Telegram bot that pairs high-definition, royalty-free commercial airplane landing and departing footage with the soul-stirring Quran recitation of **Sheikh Yasir Ad-Dosary (الشيخ ياسر الدوسري)** (Surahs 1 to 114).

Optimized in **9:16 vertical format (1080x1920)** for Facebook Reels, Instagram Reels, TikTok, and YouTube Shorts. Delivers **10x daily reels** with inspiring spiritual one-liner captions to Telegram, with instant on-demand generation capabilities from chat, deployed seamlessly on **Render** and **GitHub Actions**.

---

## 🌟 Key Features

- **🎙️ Sheikh Yasir Ad-Dosary Recitation:** Full Quran coverage (Surahs 1–114) via authentic EveryAyah CDN audio (`Yasser_Ad-Dussary_128kbps`) and AlQuran Cloud Uthmani calligraphy.
- **✈️ Royalty-Free Halal Footage:** Strictly clean commercial aviation video (runway landings, departures, twilight approaches, cockpit views). **Original audio is 100% stripped/muted** to ensure zero background music.
- **📐 9:16 Cinematic Vertical Reel (1080x1920):** Smart center-scaling, subtle gradient vignette for optimal contrast, frosted Surah header, synchronized Arabic Uthmani calligraphy with warm gold drop shadows, and clean English translations (Sahih International).
- **⏱️ Flexible Reel Duration:** Automatically creates reels tailored between **15 seconds and 90 seconds**, matching the exact constraints of Facebook Reels and Shorts.
- **💬 Spiritual One-Liner Captions:** Evocative reflections on the miracle of flight, skies, and Allah's creations, paired with Surah info, Ayah numbers, reciter credits, and viral hashtags.
- **🤖 Interactive Telegram Bot:**
  - `/generate` — Instant on-demand generation of a fresh reel directly inside the chat.
  - `/generate <surah> [ayah]` — Instant creation for a specific Surah (1–114) or Ayah (e.g. `/generate 67` or `/generate 2 255`).
  - `/status` — Live system health, uptime, and generation statistics.
  - `/daily_batch` — Trigger batch generation on demand.
- **⏰ Autonomous 10x Daily Automation:**
  - **Render Deployment:** Background scheduler (`APScheduler`) generating and posting 10 reels spaced evenly throughout the day.
  - **GitHub Actions:** Automated cron schedule (10 times a day) generating reels and dispatching them directly to Telegram with artifact backups.

---

## 📐 Architecture

```mermaid
graph TD
    User([Telegram User / Scheduler / GitHub Actions]) -->|Commands / Cron| Bot[Telegram Bot & Controller]
    
    subgraph "Core Generation Engine"
        Bot --> QService[Quran Service<br/>Yasir Ad-Dosary Audio & Text]
        Bot --> VSource[Video Source Provider<br/>Royalty-Free Plane Landing/Takeoff]
        
        QService -->|EveryAyah CDN & AlQuran API| AudioAyahs[15s-90s Recitation & Timestamps]
        VSource -->|Curated HD / Pexels / Pixabay| RawVideo[Halal Airplane Footage (Muted)]
        
        AudioAyahs --> Composer[Reel Video Composer<br/>MoviePy + Pillow 9:16 1080x1920]
        RawVideo --> Composer
        
        Composer --> DynamicOverlay[Arabic Uthmani Calligraphy<br/>+ English Translation Subtitles<br/>+ Surah Header & Progress Bar]
    end

    Composer --> FinalReel[9:16 Vertical Reel (1080x1920)]
    Bot --> CapGen[Caption Generator<br/>Spiritual One-Liner + Surah Metadata]
    
    FinalReel --> TelegramSend[Telegram Channel / Group / User Delivery]
    CapGen --> TelegramSend
    
    subgraph "Autonomous Deployment"
        Render[Render Web Service / Worker<br/>APScheduler 10x/day + Bot Polling]
        GHA[GitHub Actions Workflow<br/>Scheduled Cron / Dispatch 10x/day]
    end
    
    Render -.-> Bot
    GHA -.-> Bot
```

---

## 🚀 Quick Start (Local Setup)

### 1. Clone & Install Dependencies
Ensure you have **Python 3.10+** and **FFmpeg** installed.
```bash
git clone https://github.com/your-repo/plane_landing.git
cd plane_landing
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and provide your credentials:
```env
# Required for Telegram bot and delivery
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_CHAT_ID=-100xxxxxxxxxx

# Optional video API keys (system works out-of-the-box with CC0 catalog)
PEXELS_API_KEY=
PIXABAY_API_KEY=

# Settings
MIN_DURATION_SECONDS=15
MAX_DURATION_SECONDS=90
DAILY_GENERATION_COUNT=10
CHANNEL_TAG=@QuranInTheSky
```

### 3. Generate a Reel with Custom Surah & Verse Ranges

You have **4 flexible ways** to generate any Surah and exact verse ranges:

#### Option A: Interactive Wizard (Easiest)
Run the interactive CLI wizard:
```bash
python main.py -i
# or
python scripts/generate_custom_reel.py
```
It prompts you to choose the Surah (by number or name like `mulk` or `67`), start verse, end verse, and whether to send to Telegram!

#### Option B: Direct Command-Line Flags
```bash
# Random Surah reel (15-90s)
python main.py --mode generate

# By Surah name or number:
python main.py --mode generate --surah mulk
python main.py --mode generate --surah 67

# Exact verse range (e.g. Surah Al-Mulk, Ayahs 1 to 5):
python main.py --mode generate --surah 67 --start-ayah 1 --end-ayah 5

# Exact 90-second range and send directly to Telegram:
python main.py --mode generate --surah 55 --start-ayah 1 --end-ayah 16 --send-telegram
```

#### Option C: Dedicated Custom Reel Script
```bash
# Fast custom generation script:
python scripts/generate_custom_reel.py --surah 67 --start 1 --end 5 --send
python scripts/generate_custom_reel.py --surah baqarah --start 255 --end 255 --send
```

### 4. Run the Telegram Bot & Scheduler
```bash
python main.py --mode bot
```
The bot listens for commands and runs the 10x daily autonomous scheduler.
Inside any Telegram chat or channel with the bot, you can send:
- `/generate` — Create a fresh random Reel (15-90s)
- `/generate <surah>` — Create for a specific Surah by number or name (e.g. `/generate 67` or `/generate mulk`)
- `/generate <surah> <start_ayah> <end_ayah>` — **Exact verse range!**
  - `/generate 67 1 5` (Surah Al-Mulk, Ayahs 1 to 5)
  - `/generate mulk 1 5` (Lookup by Surah name!)
  - `/generate 55 1 16` (Surah Ar-Rahman, Ayahs 1 to 16, full 90-second reel)
  - `/generate 2 255 255` (Ayat Al-Kursi)
  - `/generate 67:1-5` or `/generate 67 1-5`
- `/surahs [query]` — Browse all Surahs, ayah counts, or search by name (e.g. `/surahs kahf`)
- `/status` — Live bot uptime, storage, and stats
- `/daily_batch` — Trigger a 10-reel batch run immediately

---

## 🤖 Telegram Bot Setup Guide

1. Open Telegram and search for **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot`, choose a name and username (e.g. `PlaneQuranReelsBot`).
3. Copy the HTTP API token into `TELEGRAM_BOT_TOKEN`.
4. **Getting your Channel / Group ID:**
   - Create a Telegram Channel or Group where your Reels will be published.
   - Add your bot as an **Administrator** with permission to post messages/videos.
   - Send a test message in the channel and forward it to **[@userinfobot](https://t.me/userinfobot)** or use `https://api.telegram.org/bot<TOKEN>/getUpdates` to find the `chat.id` (usually starts with `-100`).
   - Set `TELEGRAM_CHAT_ID=-100xxxxxxxxxx`.

---

## ☁️ Deployment on Render

This project is fully containerized and pre-configured for **Render Web Services**:

1. Push this repository to GitHub.
2. Log in to [Render.com](https://render.com/) and click **New +** -> **Web Service** (or use the Blueprint with `render.yaml`).
3. Select your repository.
4. Set the environment to **Docker**.
5. In **Environment Variables**, add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `PEXELS_API_KEY` (optional)
   - `PIXABAY_API_KEY` (optional)
6. Render will automatically build the Docker container (with Python 3.11, FFmpeg, fonts, and dependencies), start the healthcheck server on port 8080 (`/healthz`), and run the Telegram bot and 10x daily scheduler in the background.

---

## ⚡ Deployment on GitHub Actions

A ready-to-use GitHub Actions workflow is located at `.github/workflows/daily_reels.yml`.

### Setting up Secrets:
1. In your GitHub repository, go to **Settings** -> **Secrets and variables** -> **Actions**.
2. Add the following repository secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `PEXELS_API_KEY` (optional)
   - `PIXABAY_API_KEY` (optional)

### Scheduled & Manual Execution:
- **Scheduled:** The workflow automatically runs **10 times every 24 hours** at scheduled intervals:
  `00:00, 02:24, 04:48, 07:12, 09:36, 12:00, 14:24, 16:48, 19:12, 21:36 UTC`.
- **Manual Trigger:** Go to the **Actions** tab in GitHub, select **Daily 10x Quran Reels Generator**, click **Run workflow**, and optionally specify the Surah number or count.
- Generated reels are also archived as downloadable GitHub workflow artifacts for 7 days.

---

## 📁 Project Structure

```
plane_landing/
├── .github/
│   └── workflows/
│       └── daily_reels.yml       # GitHub Actions 10x daily cron & manual dispatch
├── assets/
│   ├── fonts/                   # Amiri-Bold.ttf (Arabic) & Inter-Bold.ttf (English)
│   └── videos/                  # Local custom video folder & cache
│       └── cache/               # Downloaded CC0 / royalty-free airplane clips
├── data/
│   ├── quran_cache/             # Cached Yasir Ad-Dosary MP3s and verse metadata
│   └── surahs.json              # Complete 114 Surahs offline index
├── output/                      # Rendered 9:16 vertical MP4 reels
├── src/
│   ├── __init__.py
│   ├── config.py                # Environment and configuration loader
│   ├── font_manager.py          # Font downloader and verifier
│   ├── quran_service.py         # Yasir Ad-Dosary recitation & verse sequencing (15-90s)
│   ├── video_source.py          # Royalty-free airplane video provider (CC0/Pexels/Pixabay)
│   ├── video_composer.py        # 9:16 vertical MoviePy composer with dynamic subtitles
│   ├── caption_generator.py     # Spiritual one-liner reflections & Facebook Reels tags
│   └── telegram_bot.py          # Telegram bot handlers & APScheduler 10x daily automation
├── Dockerfile                   # Multi-stage container with FFmpeg & fonts
├── render.yaml                  # Render Blueprint configuration
├── requirements.txt             # Python dependencies
├── server.py                    # FastAPI server for Render health checks + bot worker
├── main.py                      # Unified CLI entrypoint (bot / generate / batch)
└── README.md                    # Comprehensive documentation
```

---

## 🛡️ Halal & Content Assurance

1. **Pure Audio:** Only the authentic Quran recitation of Sheikh Yasir Ad-Dosary is included. Background video audio is completely stripped.
2. **Clean Footage:** Only aircraft landing on runways, departures climbing into the sky, clouds, and cockpit perspectives. No human faces, inappropriate clothing, or non-halal themes.
3. **Spiritual Alignment:** Captions and visual presentation are crafted to instill peace, awe of creation, and remembrance of Allah SWT.

---

## 📜 License
This project is open-source under the MIT License. Recitations courtesy of EveryAyah / Quran.com / Sheikh Yasir Al-Dosari. Curated video footage is CC0 / Public Domain / Pexels License.
