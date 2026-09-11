import os
import json
import random
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from mutagen.mp3 import MP3
import moviepy.editor as mp

from src.config import (
    DATA_DIR,
    QURAN_CACHE_DIR,
    QURAN_RECITER_ID,
    RECITER_NAME_EN,
    RECITER_NAME_AR,
    MIN_DURATION_SECONDS,
    MAX_DURATION_SECONDS,
)

logger = logging.getLogger(__name__)

EVERYAYAH_BASE_URL = f"https://everyayah.com/data/{QURAN_RECITER_ID}"
ALQURAN_API_URL = "https://api.alquran.cloud/v1/ayah"

class QuranService:
    def __init__(self):
        self.surahs_file = DATA_DIR / "surahs.json"
        self.surahs_data = self._load_surahs()

    def _load_surahs(self) -> Dict[int, dict]:
        if not self.surahs_file.exists():
            raise FileNotFoundError(f"Surahs metadata not found at {self.surahs_file}")
        with open(self.surahs_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}

    def get_surah_info(self, surah_number: int) -> dict:
        surah_number = int(surah_number)
        if surah_number not in self.surahs_data:
            raise ValueError(f"Invalid surah number {surah_number}. Must be between 1 and 114.")
        return self.surahs_data[surah_number]

    def get_audio_path(self, surah: int, ayah: int) -> Path:
        filename = f"{surah:03d}{ayah:03d}.mp3"
        return QURAN_CACHE_DIR / filename

    def get_text_cache_path(self, surah: int, ayah: int) -> Path:
        filename = f"{surah:03d}{ayah:03d}.json"
        return QURAN_CACHE_DIR / filename

    def download_ayah_audio(self, surah: int, ayah: int) -> Path:
        """Download individual ayah audio from EveryAyah if not already cached."""
        target_path = self.get_audio_path(surah, ayah)
        if target_path.exists() and target_path.stat().st_size > 500:
            return target_path

        url = f"{EVERYAYAH_BASE_URL}/{surah:03d}{ayah:03d}.mp3"
        logger.info(f"Downloading Yasir Ad-Dosary audio: Surah {surah} Ayah {ayah} from {url}")
        
        resp = requests.get(url, timeout=25)
        if resp.status_code == 200 and len(resp.content) > 500:
            with open(target_path, "wb") as f:
                f.write(resp.content)
            return target_path
        else:
            raise RuntimeError(f"Failed to download audio for Surah {surah} Ayah {ayah}: HTTP {resp.status_code}")

    def fetch_ayah_text(self, surah: int, ayah: int) -> Tuple[str, str]:
        """Fetch Arabic text and English translation for a given ayah."""
        cache_path = self.get_text_cache_path(surah, ayah)
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data["arabic"], data["english"]
            except Exception:
                pass

        url = f"{ALQURAN_API_URL}/{surah}:{ayah}/editions/quran-uthmani,en.sahih"
        logger.info(f"Fetching text for Surah {surah} Ayah {ayah} from AlQuran Cloud API")
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            res_data = resp.json().get("data", [])
            arabic_text = res_data[0]["text"].strip()
            english_text = res_data[1]["text"].strip()

            # Clean leading bismillah if not Al-Fatihah or if prefixed
            if surah != 1 and ayah == 1:
                bismillah = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
                bismillah_simple = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
                if arabic_text.startswith(bismillah):
                    arabic_text = arabic_text[len(bismillah):].strip()
                elif arabic_text.startswith(bismillah_simple):
                    arabic_text = arabic_text[len(bismillah_simple):].strip()

            # Cache the result
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"arabic": arabic_text, "english": english_text}, f, ensure_ascii=False)

            return arabic_text, english_text
        else:
            raise RuntimeError(f"Failed to fetch text for Surah {surah} Ayah {ayah}: HTTP {resp.status_code}")

    def get_ayah_duration(self, audio_path: Path) -> float:
        """Accurately measure audio duration in seconds using mutagen."""
        audio = MP3(str(audio_path))
        return float(audio.info.length)

    def select_ayah_sequence(
        self,
        surah_number: Optional[int] = None,
        start_ayah: Optional[int] = None,
        min_sec: float = MIN_DURATION_SECONDS,
        max_sec: float = MAX_DURATION_SECONDS,
    ) -> dict:
        """
        Selects a sequence of consecutive ayahs matching duration constraints [min_sec, max_sec].
        If surah_number is not provided, randomly selects a surah from 1 to 114.
        """
        if surah_number is None:
            surah_number = random.randint(1, 114)
        
        surah_info = self.get_surah_info(surah_number)
        total_ayahs = surah_info["numberOfAyahs"]

        if start_ayah is None or start_ayah < 1 or start_ayah > total_ayahs:
            start_ayah = random.randint(1, total_ayahs)

        selected_ayahs = []
        current_duration = 0.0

        attempts = 0
        while attempts < 8:
            selected_ayahs = []
            current_duration = 0.0
            curr = start_ayah

            while curr <= total_ayahs and current_duration < max_sec:
                try:
                    audio_path = self.download_ayah_audio(surah_number, curr)
                    dur = self.get_ayah_duration(audio_path)
                except Exception as e:
                    logger.warning(f"Could not load audio for {surah_number}:{curr}: {e}")
                    break

                if current_duration + dur > max_sec and len(selected_ayahs) > 0:
                    break

                arabic_text, english_text = self.fetch_ayah_text(surah_number, curr)
                
                selected_ayahs.append({
                    "ayah_number": curr,
                    "arabic_text": arabic_text,
                    "english_text": english_text,
                    "audio_path": str(audio_path),
                    "duration": dur,
                })
                current_duration += dur
                curr += 1

                if current_duration >= min_sec:
                    break

            if current_duration >= min_sec:
                break

            # If not reached min_sec and curr > total_ayahs, shift starting ayah backward
            if start_ayah > 1:
                start_ayah = max(1, start_ayah - 2)
            else:
                # If we are at Ayah 1 and still under min_sec, accept if >= 10s or try another surah
                if current_duration >= 10.0:
                    break
                surah_number = random.randint(1, 114)
                surah_info = self.get_surah_info(surah_number)
                total_ayahs = surah_info["numberOfAyahs"]
                start_ayah = random.randint(1, total_ayahs)

            attempts += 1

        if not selected_ayahs:
            raise RuntimeError(f"Could not construct valid ayah sequence for Surah {surah_number}")

        # Combine audio using MoviePy
        clips = []
        timed_ayahs = []
        timeline_cursor = 0.0

        for item in selected_ayahs:
            clip = mp.AudioFileClip(item["audio_path"])
            dur = clip.duration
            timed_ayahs.append({
                **item,
                "start_time": timeline_cursor,
                "end_time": timeline_cursor + dur,
            })
            clips.append(clip)
            timeline_cursor += dur

        combined_audio = mp.concatenate_audioclips(clips)
        combined_filename = f"recitation_s{surah_number}_a{timed_ayahs[0]['ayah_number']}_to_a{timed_ayahs[-1]['ayah_number']}.mp3"
        combined_path = QURAN_CACHE_DIR / combined_filename
        
        # Write the combined audio file
        combined_audio.write_audiofile(str(combined_path), fps=44100, logger=None)
        
        # Close individual clips
        for c in clips:
            c.close()
        combined_audio.close()

        return {
            "surah_number": surah_number,
            "surah_name_en": surah_info["englishName"],
            "surah_name_ar": surah_info["name"],
            "surah_translation": surah_info["englishNameTranslation"],
            "start_ayah": timed_ayahs[0]["ayah_number"],
            "end_ayah": timed_ayahs[-1]["ayah_number"],
            "ayah_count": len(timed_ayahs),
            "ayahs": timed_ayahs,
            "total_duration": timeline_cursor,
            "combined_audio_path": combined_path,
            "reciter_en": RECITER_NAME_EN,
            "reciter_ar": RECITER_NAME_AR,
        }

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    logging.basicConfig(level=logging.INFO)
    qs = QuranService()
    res = qs.select_ayah_sequence(surah_number=67, start_ayah=1)
    print(f"Generated Surah: {res['surah_name_en']} ({res['surah_name_ar']})")
    print(f"Ayahs: {res['start_ayah']} - {res['end_ayah']}, Duration: {res['total_duration']:.2f}s")
    for a in res["ayahs"]:
        print(f"  Ayah {a['ayah_number']} [{a['start_time']:.1f}s -> {a['end_time']:.1f}s]: {a['english_text'][:60]}...")
