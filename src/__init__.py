"""
Autonomous Airplane Landing & Departing Quran Reels System
Featuring Sheikh Yasir Ad-Dosary recitation and 9:16 vertical video composition.
"""

__version__ = "1.0.0"

# Fix for Pillow 10+ where Image.ANTIALIAS was removed, causing MoviePy resize() to fail
try:
    from PIL import Image
    if not hasattr(Image, "ANTIALIAS"):
        Image.ANTIALIAS = getattr(Image, "Resampling", Image).LANCZOS
except ImportError:
    pass

