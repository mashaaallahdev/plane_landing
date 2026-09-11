import os
import random
import logging
import requests
from pathlib import Path
from typing import List, Optional

from src.config import (
    VIDEOS_DIR,
    VIDEO_CACHE_DIR,
    PEXELS_API_KEY,
    PIXABAY_API_KEY,
)

logger = logging.getLogger(__name__)

# Curated catalog of direct public domain / CC commercial airplane landing and departure videos
CURATED_AVIATION_VIDEOS = [
    {
        "id": "landing_haneda",
        "title": "Aircraft Landing at Haneda Runway",
        "type": "landing",
        "url": "https://upload.wikimedia.org/wikipedia/commons/2/21/Landing_aircraft_-_Haneda_-_2021_3_31.webm",
        "ext": ".webm",
    },
    {
        "id": "landing_hkia",
        "title": "Commercial Jet Landing at HKIA Runway",
        "type": "landing",
        "url": "https://upload.wikimedia.org/wikipedia/commons/f/f7/An_Airplane_landing_at_HKIA_202010311319.webm",
        "ext": ".webm",
    },
    {
        "id": "landing_timelapse",
        "title": "Airplane Landing Runway Approach Timelapse",
        "type": "landing",
        "url": "https://upload.wikimedia.org/wikipedia/commons/a/aa/Airplane_Landing_Timelapse.webm",
        "ext": ".webm",
    },
    {
        "id": "landing_night_kathmandu",
        "title": "Night Runway Lights Airplane Landing",
        "type": "landing",
        "url": "https://upload.wikimedia.org/wikipedia/commons/9/91/Kathmandu_airport_landing_night.webm",
        "ext": ".webm",
    },
    {
        "id": "takeoff_fuerteventura",
        "title": "Passenger Jet Takeoff Runway Climb",
        "type": "takeoff",
        "url": "https://upload.wikimedia.org/wikipedia/commons/3/3b/Takeoff_from_Fuerteventura.webm",
        "ext": ".webm",
    },
    {
        "id": "takeoff_737_pdx",
        "title": "Boeing 737 Runway Departure",
        "type": "takeoff",
        "url": "https://upload.wikimedia.org/wikipedia/commons/8/81/United_Airlines_N69826_737-900ER_Takeoff_Portland_Airport_%28PDX%29.webm",
        "ext": ".webm",
    },
    {
        "id": "takeoff_llet",
        "title": "Twin Engine Aircraft Takeoff",
        "type": "takeoff",
        "url": "https://upload.wikimedia.org/wikipedia/commons/d/d9/4X-ATI_takeoff_LLET_14-02-2019.webm",
        "ext": ".webm",
    },
]

class VideoSourceProvider:
    def __init__(self):
        VIDEO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    def get_local_custom_videos(self) -> List[Path]:
        """Find any custom videos dropped by the user into assets/videos/ (excluding cache)."""
        valid_exts = {".mp4", ".mov", ".mkv", ".webm"}
        custom = [
            f for f in VIDEOS_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in valid_exts and not f.name.startswith(".")
        ]
        return custom

    def fetch_from_pexels(self, query: str = "airplane landing") -> Optional[Path]:
        """Fetch video from Pexels API if API key is provided."""
        if not PEXELS_API_KEY:
            return None

        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": PEXELS_API_KEY}
        params = {
            "query": query,
            "per_page": 10,
            "orientation": "portrait",  # Also can search landscape and smart-crop
        }
        try:
            r = requests.get(url, headers=headers, params=params, timeout=15)
            if r.ok:
                data = r.json()
                videos = data.get("videos", [])
                if videos:
                    chosen = random.choice(videos)
                    # Pick highest quality mp4 video file up to 1080p (exclude 4K UHD / 1440p to prevent Render OOM)
                    files = chosen.get("video_files", [])
                    mp4s = [f for f in files if f.get("file_type") == "video/mp4"]
                    if mp4s:
                        suitable = [
                            f for f in mp4s
                            if (f.get("height", 0) or 0) <= 1920 and (f.get("width", 0) or 0) <= 1920
                        ]
                        if suitable:
                            suitable.sort(key=lambda x: (x.get("height", 0) or 0) * (x.get("width", 0) or 0), reverse=True)
                            target_file = suitable[0]
                        else:
                            mp4s.sort(key=lambda x: (x.get("height", 0) or 0) * (x.get("width", 0) or 0))
                            target_file = mp4s[0]

                        vurl = target_file.get("link")
                        vid_id = chosen.get("id")
                        dest = VIDEO_CACHE_DIR / f"pexels_{vid_id}.mp4"
                        if not dest.exists():
                            logger.info(f"Downloading Pexels video {vid_id} ({target_file.get('width')}x{target_file.get('height')})...")
                            with requests.get(vurl, stream=True, timeout=45) as vr:
                                if vr.ok:
                                    with open(dest, "wb") as f:
                                        for chunk in vr.iter_content(chunk_size=1024 * 1024):
                                            if chunk:
                                                f.write(chunk)
                                    return dest
                        else:
                            return dest
        except Exception as e:
            logger.warning(f"Failed to fetch from Pexels: {e}")
        return None

    def fetch_from_pixabay(self, query: str = "airplane") -> Optional[Path]:
        """Fetch video from Pixabay API if API key is provided."""
        if not PIXABAY_API_KEY:
            return None

        url = "https://pixabay.com/api/videos/"
        params = {
            "key": PIXABAY_API_KEY,
            "q": query,
            "video_type": "film",
            "per_page": 10,
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.ok:
                hits = r.json().get("hits", [])
                if hits:
                    chosen = random.choice(hits)
                    videos_dict = chosen.get("videos", {})
                    # Prefer medium (720p/1080p) over large/4k
                    target_info = videos_dict.get("medium") or videos_dict.get("large") or videos_dict.get("small")
                    if target_info and target_info.get("url"):
                        vurl = target_info["url"]
                        dest = VIDEO_CACHE_DIR / f"pixabay_{chosen['id']}.mp4"
                        if not dest.exists():
                            logger.info(f"Downloading Pixabay video {chosen['id']}...")
                            with requests.get(vurl, stream=True, timeout=45) as vr:
                                if vr.ok:
                                    with open(dest, "wb") as f:
                                        for chunk in vr.iter_content(chunk_size=1024 * 1024):
                                            if chunk:
                                                f.write(chunk)
                                    return dest
                        else:
                            return dest
        except Exception as e:
            logger.warning(f"Failed to fetch from Pixabay: {e}")
        return None

    def download_curated_video(self, video_entry: dict) -> Path:
        """Download and cache a curated CC0 / Public Domain aviation video."""
        filename = f"{video_entry['id']}{video_entry['ext']}"
        target_path = VIDEO_CACHE_DIR / filename
        if target_path.exists() and target_path.stat().st_size > 10000:
            return target_path

        logger.info(f"Downloading curated aviation video '{video_entry['title']}'...")
        headers = {"User-Agent": "PlaneLandingQuranBot/1.0 (AviationQuranBot)"}
        with requests.get(video_entry["url"], headers=headers, stream=True, timeout=45) as resp:
            if resp.ok:
                with open(target_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                if target_path.stat().st_size > 10000:
                    logger.info(f"Curated video cached to {target_path}")
                    return target_path
        raise RuntimeError(f"Failed to download curated video {video_entry['id']}")

    def get_cached_videos(self) -> List[Path]:
        """Return list of valid cached videos."""
        valid_exts = {".mp4", ".mov", ".mkv", ".webm"}
        return [
            f for f in VIDEO_CACHE_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in valid_exts and f.stat().st_size > 50000
        ]

    def get_airplane_video(self, preferred_type: Optional[str] = None) -> Path:
        """
        Retrieves a clean, royalty-free airplane landing or departing video file.
        Priority:
        1. Local custom videos in assets/videos/
        2. Existing cached videos in assets/videos/cache/ (randomized for diversity)
        3. Dynamic Pexels / Pixabay if API keys provided
        4. Curated direct CC0 / Public Domain aviation catalog
        """
        # 1. Custom videos
        custom_videos = self.get_local_custom_videos()
        if custom_videos:
            chosen = random.choice(custom_videos)
            logger.info(f"Using user custom video: {chosen.name}")
            return chosen

        # 2. Check if we already have cached videos, and 70% of the time pick from cache to avoid rate limits
        cached_videos = self.get_cached_videos()
        if cached_videos and (random.random() < 0.7 or not PEXELS_API_KEY):
            chosen = random.choice(cached_videos)
            logger.info(f"Using cached aviation video: {chosen.name}")
            return chosen

        # 3. Pexels (if API key available)
        if PEXELS_API_KEY:
            queries = [
                "airplane landing runway",
                "airplane takeoff",
                "commercial plane landing",
                "aircraft departure",
                "runway airplane cockpit",
            ]
            q = random.choice(queries)
            vid = self.fetch_from_pexels(q)
            if vid and vid.exists():
                return vid

        # 4. Pixabay (if API key available)
        if PIXABAY_API_KEY:
            vid = self.fetch_from_pixabay("airplane landing")
            if vid and vid.exists():
                return vid

        # 5. If cached videos exist and external fetch not performed, return cached
        if cached_videos:
            chosen = random.choice(cached_videos)
            logger.info(f"Using cached aviation video: {chosen.name}")
            return chosen

        # 6. Curated aviation catalog (try multiple with graceful fallback)
        candidates = list(CURATED_AVIATION_VIDEOS)
        random.shuffle(candidates)
        for entry in candidates:
            try:
                return self.download_curated_video(entry)
            except Exception as e:
                logger.warning(f"Could not download {entry['id']}: {e}. Trying next...")

        # If all failed but cache has something
        if cached_videos:
            return cached_videos[0]

        raise RuntimeError("No airplane videos available. Please place an MP4 in assets/videos/")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    provider = VideoSourceProvider()
    video_path = provider.get_airplane_video()
    print("Obtained airplane video path:", video_path)
