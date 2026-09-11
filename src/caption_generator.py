import random
from typing import List, Dict

SPIRITUAL_ONE_LINERS = [
    "✈️ *\"Do they not see the birds suspended in the atmosphere of the sky? None holds them up except Allah.\"* — Reflect upon the signs of the Creator as you ascend into peace. 🤍",
    "🛫 *Every voyage reminds us of our journey back to our Creator.* Let these soothing verses bring tranquility to your heart today.",
    "🛬 *Descend into serene stillness.* As the wings meet the runway, may your soul find unwavering peace in His remembrance.",
    "☁️ *Drifting through the boundless heavens, between the clouds and the earth.* Listen closely to the eternal guidance of Allah.",
    "✨ *\"He created the heavens and the earth in truth; High is He above what they associate with Him.\"* Witness His infinite majesty in every flight.",
    "🤍 *In the calm expanse of the skies, let your burdens depart and divine peace touch down softly.*",
    "🌅 *Above the golden clouds, the boundless power of the Creator unfolds.* Breathe in the tranquility of the Holy Quran.",
    "✈️ *No destination is unreachable when your soul is anchored in faith.* Immerse your heart in the blessed recitation of Sheikh Yasir Al-Dosari.",
    "🕊️ *\"Verily, in the remembrance of Allah do hearts find rest.\"* (13:28) — Find peace in the rhythm of the runway and the recitation of His words.",
    "🛫 *Ascending beyond worldly noise into the divine peace of the Quran.* May your day be blessed with tranquility and ease.",
    "🛬 *Safe landings and softened hearts.* Let these verses be a sanctuary of calm for your soul today.",
    "✨ *Reflect upon the marvel of flight and the greater marvel of the One who holds the heavens from falling.*",
]

HASHTAGS = (
    "#Quran #YasirAlDosari #QuranRecitation #AirplaneLanding #AirplaneDeparture "
    "#Aviation #Flight #FacebookReels #IslamicReels #Peace #QuranTilawat #Islam #Shorts"
)

class CaptionGenerator:
    @staticmethod
    def generate_caption(quran_data: dict) -> str:
        """
        Generates an elegant, spiritual caption formatted for Telegram and Facebook Reels.
        """
        surah_en = quran_data.get("surah_name_en", "Al-Quran")
        surah_ar = quran_data.get("surah_name_ar", "")
        start_ayah = quran_data.get("start_ayah", 1)
        end_ayah = quran_data.get("end_ayah", 1)
        reciter_en = quran_data.get("reciter_en", "Sheikh Yasir Al-Dosari")
        reciter_ar = quran_data.get("reciter_ar", "الشيخ ياسر الدوسري")
        
        # Pick a beautiful one-liner hook
        hook = random.choice(SPIRITUAL_ONE_LINERS)

        # Ayah range format
        ayah_range_str = f"Ayah {start_ayah}" if start_ayah == end_ayah else f"Ayahs {start_ayah}-{end_ayah}"

        # Combine English translation preview (first 1-2 verses or summary)
        ayahs: List[Dict] = quran_data.get("ayahs", [])
        english_snippet = ""
        if ayahs:
            combined_en = " ".join(a.get("english_text", "") for a in ayahs)
            if len(combined_en) > 300:
                english_snippet = f'"{combined_en[:297]}..."'
            else:
                english_snippet = f'"{combined_en}"'

        # Build full caption
        caption = (
            f"{hook}\n\n"
            f"📖 **Surah {surah_en}** ({surah_ar})\n"
            f"📍 **{ayah_range_str}**\n"
            f"🎙️ **Reciter:** {reciter_en} ({reciter_ar})\n\n"
            f"📜 **Translation (Sahih International):**\n"
            f"{english_snippet}\n\n"
            f"{HASHTAGS}"
        )
        return caption

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    test_data = {
        "surah_name_en": "Al-Mulk",
        "surah_name_ar": "سُورَةُ المُلۡكِ",
        "start_ayah": 1,
        "end_ayah": 2,
        "reciter_en": "Sheikh Yasir Al-Dosari",
        "reciter_ar": "الشيخ ياسر الدوسري",
        "ayahs": [
            {"english_text": "Blessed is He in whose hand is dominion, and He is over all things competent."},
            {"english_text": "[He] who created death and life to test you [as to] which of you is best in deed."}
        ]
    }
    print(CaptionGenerator.generate_caption(test_data))
