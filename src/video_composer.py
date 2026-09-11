import os
import textwrap
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# Compatibility fix for Pillow 10+ where Image.ANTIALIAS was removed
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = getattr(Image, "Resampling", Image).LANCZOS

import moviepy.editor as mp
from moviepy.video.fx.all import crop, resize
import moviepy.video.fx.resize as fx_resize

# Ensure moviepy's internal resizer never crashes on Pillow 10+
if hasattr(fx_resize, "resizer") and getattr(fx_resize.resizer, "origin", "") == "PIL":
    def _patched_pil_resizer(pic, newsize):
        newsize = list(map(int, newsize))[::-1]
        pilim = Image.fromarray(pic)
        resampling = getattr(Image, "Resampling", Image)
        filt = getattr(resampling, "LANCZOS", getattr(Image, "ANTIALIAS", None))
        resized_pil = pilim.resize(newsize[::-1], filt)
        return np.array(resized_pil)
    fx_resize.resizer = _patched_pil_resizer

from src.config import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
    OUTPUT_DIR,
    ASSETS_DIR,
    ARABIC_FONT_PATH,
    ENGLISH_FONT_PATH,
    CHANNEL_TAG,
    RECITER_NAME_EN,
)
from src.font_manager import ensure_fonts

logger = logging.getLogger(__name__)

from PIL import features

HAS_RAQM = bool(features.check("raqm"))

# Reshaper instance with complete Harakat (Tashkeel) support (fallback for systems without libraqm)
arabic_reshaper_with_harakat = arabic_reshaper.ArabicReshaper(configuration={
    "delete_harakat": False,
    "support_ligatures": True,
})

def prepare_arabic_text(text: str) -> Tuple[str, Optional[str]]:
    """
    Prepares Arabic text for Pillow rendering across different environments:
    - On Linux / Docker / GitHub Actions with libraqm: Pillow natively shapes (HarfBuzz)
      and layouts (FriBidi) Arabic text right-to-left. Applying python-bidi or arabic_reshaper
      causes double-bidi reversal resulting in mirrored/backwards text!
      Therefore, we pass raw Arabic text with direction='rtl'.
    - On Windows / systems without libraqm: Pillow's standard FreeType engine lacks complex
      text layout, so we use arabic_reshaper and python-bidi to pre-shape and pre-reverse.
    """
    if HAS_RAQM:
        return text, "rtl"
    else:
        reshaped = arabic_reshaper_with_harakat.reshape(text)
        return get_display(reshaped), None

def reshape_arabic(text: str) -> str:
    """Legacy helper for non-directional contexts."""
    res, _ = prepare_arabic_text(text)
    return res

def wrap_arabic_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wraps Arabic text properly according to measured pixel width with harkat."""
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        line_to_draw, direction = prepare_arabic_text(test_line)
        if direction:
            bbox = draw.textbbox((0, 0), line_to_draw, font=font, direction=direction)
        else:
            bbox = draw.textbbox((0, 0), line_to_draw, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def create_gradient_mask(width: int, height: int) -> Image.Image:
    """
    Creates a full-frame RGBA overlay with subtle dark gradients at the top and bottom
    to maximize text legibility on bright sky / runway backgrounds.
    """
    base = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)

    # Top gradient (height ~ 320px)
    top_h = 320
    for y in range(top_h):
        # 160 -> 0 alpha
        alpha = int(160 * (1.0 - (y / top_h) ** 1.5))
        draw.line([(0, y), (width, y)], fill=(10, 15, 26, alpha))

    # Bottom gradient (height ~ 600px)
    bot_h = 600
    for y in range(bot_h):
        # 0 -> 180 alpha
        alpha = int(180 * ((y / bot_h) ** 1.5))
        draw.line([(0, height - bot_h + y), (width, height - bot_h + y)], fill=(10, 15, 26, alpha))

    return base

def render_ayah_overlay(
    ayah_data: dict,
    surah_name_en: str,
    surah_name_ar: str,
    total_ayah_count: int,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
) -> np.ndarray:
    """
    Renders the graphical overlay for a specific Ayah as an RGBA numpy array.
    Features:
    - Glass effect container for Surah Name Header (Top)
    - Floating Quran Verses with Harkat (Tashkeel) and drop shadows (No glass container)
    - Custom Watermark at bottom-left
    """
    ensure_fonts()
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Load fonts
    font_header_title = ImageFont.truetype(str(ENGLISH_FONT_PATH), 32)
    font_header_sub = ImageFont.truetype(str(ENGLISH_FONT_PATH), 24)
    font_header_ar = ImageFont.truetype(str(ARABIC_FONT_PATH), 28)
    font_arabic = ImageFont.truetype(str(ARABIC_FONT_PATH), 54)
    font_english = ImageFont.truetype(str(ENGLISH_FONT_PATH), 32)
    font_brand = ImageFont.truetype(str(ENGLISH_FONT_PATH), 22)

    # 1. Top Header: Glass effect container for Surah Name
    header_box = (60, 100, width - 60, 220)
    draw.rounded_rectangle(header_box, radius=24, fill=(15, 23, 42, 190), outline=(255, 255, 255, 40), width=2)

    title_en = f"SURAH {surah_name_en.upper()}"
    clean_surah_ar = surah_name_ar.strip()
    if not (clean_surah_ar.startswith("سورة") or clean_surah_ar.startswith("سُورَةُ")):
        clean_surah_ar = f"سورة {clean_surah_ar}"
    
    header_ar_text, header_dir = prepare_arabic_text(clean_surah_ar)
    
    # English title inside glass container
    draw.text((90, 122), title_en, font=font_header_title, fill=(255, 255, 255, 255))
    
    # Arabic Surah Name on the right inside glass container
    if header_dir:
        bbox_ar = draw.textbbox((0, 0), header_ar_text, font=font_header_ar, direction=header_dir)
        w_ar = bbox_ar[2] - bbox_ar[0]
        draw.text((width - 90 - w_ar, 124), header_ar_text, font=font_header_ar, fill=(245, 158, 11, 255), direction=header_dir)
    else:
        bbox_ar = draw.textbbox((0, 0), header_ar_text, font=font_header_ar)
        w_ar = bbox_ar[2] - bbox_ar[0]
        draw.text((width - 90 - w_ar, 124), header_ar_text, font=font_header_ar, fill=(245, 158, 11, 255))

    # Subtitle line: Ayah number + Reciter
    ayah_num = ayah_data.get("ayah_number", 1)
    sub_text = f"Ayah {ayah_num}  •  Reciter: {RECITER_NAME_EN}"
    draw.text((90, 168), sub_text, font=font_header_sub, fill=(203, 213, 225, 230))

    # 2. Main Quran Verse Text: Floating directly over footage (NO glass container, with full Harkat)
    arabic_raw = ayah_data.get("arabic_text", "")
    english_raw = ayah_data.get("english_text", "")

    # Wrap Arabic lines (with full harkat)
    ar_lines = wrap_arabic_text(arabic_raw, font_arabic, width - 160, draw)
    
    # Wrap English lines
    en_lines = textwrap.wrap(english_raw, width=42)

    line_h_ar = 82
    line_h_en = 44
    content_h = (len(ar_lines) * line_h_ar) + 20 + (len(en_lines) * line_h_en)

    # Position content at comfortable lower-center area
    cur_y = height - 340 - content_h

    # Draw Arabic text lines with Harkat (Centered with rich multi-directional shadow)
    for line in ar_lines:
        line_to_draw, direction = prepare_arabic_text(line)
        if direction:
            bbox = draw.textbbox((0, 0), line_to_draw, font=font_arabic, direction=direction)
        else:
            bbox = draw.textbbox((0, 0), line_to_draw, font=font_arabic)
        w = bbox[2] - bbox[0]
        x = (width - w) // 2

        # Multi-layer outer shadow for high readability on any background
        for ox, oy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 3), (0, -3), (3, 0), (-3, 0)]:
            if direction:
                draw.text((x + ox, cur_y + oy), line_to_draw, font=font_arabic, fill=(0, 0, 0, 240), direction=direction)
            else:
                draw.text((x + ox, cur_y + oy), line_to_draw, font=font_arabic, fill=(0, 0, 0, 240))
        # Warm ivory glowing Arabic text
        if direction:
            draw.text((x, cur_y), line_to_draw, font=font_arabic, fill=(254, 249, 195, 255), direction=direction)
        else:
            draw.text((x, cur_y), line_to_draw, font=font_arabic, fill=(254, 249, 195, 255))
        cur_y += line_h_ar

    cur_y += 18

    # Draw English Translation lines (Centered with drop shadow)
    for line in en_lines:
        bbox = draw.textbbox((0, 0), line, font=font_english)
        w = bbox[2] - bbox[0]
        x = (width - w) // 2
        for ox, oy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 2)]:
            draw.text((x + ox, cur_y + oy), line, font=font_english, fill=(0, 0, 0, 220))
        draw.text((x, cur_y), line, font=font_english, fill=(248, 250, 252, 255))
        cur_y += line_h_en

    # 3. Watermark at Bottom Left (Semi-transparent so background content remains visible)
    watermark_path = ASSETS_DIR / "watermark.png"
    if watermark_path.exists():
        try:
            wm = Image.open(watermark_path).convert("RGBA")
            wm_size = 130
            wm = wm.resize((wm_size, wm_size), Image.LANCZOS)

            # Reduce opacity to ~45% for transparency
            r, g, b, a = wm.split()
            a = a.point(lambda p: int(p * 0.45))
            wm_transparent = Image.merge("RGBA", (r, g, b, a))

            wm_x = 60
            wm_y = height - wm_size - 70
            canvas.paste(wm_transparent, (wm_x, wm_y), wm_transparent)
        except Exception as e:
            logger.warning(f"Failed to paste watermark: {e}")
    elif CHANNEL_TAG:
        bbox_tag = draw.textbbox((0, 0), CHANNEL_TAG, font=font_brand)
        draw.text((60, height - 90), CHANNEL_TAG, font=font_brand, fill=(226, 232, 240, 160))

    return np.array(canvas)

class VideoComposer:
    def __init__(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ensure_fonts()

    def process_background_video(self, video_path: Path, target_duration: float) -> mp.VideoClip:
        """
        Scales, crops to 9:16 vertical (1080x1920), loops or trims to match target_duration,
        and ensures the original video's audio is 100% stripped/muted.
        """
        clip = mp.VideoFileClip(str(video_path))
        # Completely remove any audio from original footage
        clip = clip.without_audio()

        # Scale and center-crop to 1080x1920
        w, h = clip.size
        target_w, target_h = VIDEO_WIDTH, VIDEO_HEIGHT

        scale_factor = max(target_w / w, target_h / h)
        new_w = int(round(w * scale_factor))
        new_h = int(round(h * scale_factor))
        
        # Ensure dimensions are even numbers
        if new_w % 2 != 0:
            new_w += 1
        if new_h % 2 != 0:
            new_h += 1

        scaled_clip = clip.resize((new_w, new_h))
        cropped_clip = scaled_clip.crop(
            x_center=new_w / 2,
            y_center=new_h / 2,
            width=target_w,
            height=target_h
        )

        # Match duration: loop if shorter, trim if longer
        if cropped_clip.duration < target_duration:
            # Loop clip
            n_loops = int(np.ceil(target_duration / cropped_clip.duration))
            looped = mp.concatenate_videoclips([cropped_clip] * n_loops)
            final_bg = looped.subclip(0, target_duration)
        else:
            final_bg = cropped_clip.subclip(0, target_duration)

        return final_bg

    def compose_reel(self, video_path: Path, quran_data: dict) -> Path:
        """
        Assembles the complete 9:16 vertical Facebook Reel video:
        1. Clean airplane background video (muted)
        2. Soft gradient overlay masks
        3. Synchronized Arabic calligraphy and English translation subtitle overlays
        4. Sheikh Yasir Ad-Dosary recitation audio track
        """
        total_duration = quran_data["total_duration"]
        logger.info(f"Composing 9:16 Reel for Surah {quran_data['surah_name_en']} (Duration: {total_duration:.2f}s)")

        # 1. Prepare Background Video
        bg_clip = self.process_background_video(video_path, total_duration)

        # 2. Gradient Vignette Overlay
        grad_img = create_gradient_mask(VIDEO_WIDTH, VIDEO_HEIGHT)
        grad_arr = np.array(grad_img)
        grad_clip = mp.ImageClip(grad_arr).set_duration(total_duration)

        # 3. Synchronized Ayah Overlays
        surah_en = quran_data["surah_name_en"]
        surah_ar = quran_data["surah_name_ar"]
        ayahs: List[dict] = quran_data["ayahs"]
        
        overlay_clips = []
        for a in ayahs:
            start_t = a["start_time"]
            end_t = min(a["end_time"], total_duration)
            dur = max(0.1, end_t - start_t)

            frame_arr = render_ayah_overlay(
                ayah_data=a,
                surah_name_en=surah_en,
                surah_name_ar=surah_ar,
                total_ayah_count=quran_data["ayah_count"],
            )

            # Create ImageClip for this Ayah segment
            img_clip = (
                mp.ImageClip(frame_arr)
                .set_start(start_t)
                .set_duration(dur)
            )
            overlay_clips.append(img_clip)

        # 4. Audio track: Sheikh Yasir Ad-Dosary recitation with subtle audio fades
        audio_clip = mp.AudioFileClip(str(quran_data["combined_audio_path"]))
        # Audio fade in (0.4s) and fade out (0.8s)
        audio_clip = audio_clip.audio_fadein(0.4).audio_fadeout(0.8)

        # 5. Composite Video
        all_clips = [bg_clip, grad_clip] + overlay_clips
        final_video = mp.CompositeVideoClip(all_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
        final_video = final_video.set_duration(total_duration).set_audio(audio_clip)

        # 6. Export Final MP4 File
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        surah_slug = surah_en.lower().replace(" ", "_").replace("-", "_")
        filename = f"reel_{surah_slug}_s{quran_data['surah_number']}_a{quran_data['start_ayah']}_{timestamp_str}.mp4"
        output_file = OUTPUT_DIR / filename

        # Dynamically calculate video bitrate so file stays strictly under Telegram's 50MB limit (target max 40MB)
        target_max_mb = 40.0
        target_bitrate_kbps = int((target_max_mb * 8 * 1024) / max(1.0, total_duration)) - 192
        safe_bitrate = max(1800, min(target_bitrate_kbps, 4000))
        bitrate_str = f"{safe_bitrate}k"

        logger.info(f"Rendering video to {output_file} at {VIDEO_FPS} fps (Bitrate: {bitrate_str})...")
        final_video.write_videofile(
            str(output_file),
            fps=VIDEO_FPS,
            codec="libx264",
            audio_codec="aac",
            bitrate=bitrate_str,
            audio_bitrate="192k",
            preset="fast",
            threads=4,
            logger=None,  # Suppress internal MoviePy stdout clutter
        )

        # Clean up clips to free memory
        final_video.close()
        bg_clip.close()
        grad_clip.close()
        audio_clip.close()
        for oc in overlay_clips:
            oc.close()

        logger.info(f"Reel successfully rendered: {output_file}")
        return output_file

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    logging.basicConfig(level=logging.INFO)

    from src.quran_service import QuranService
    from src.video_source import VideoSourceProvider

    qs = QuranService()
    vs = VideoSourceProvider()
    composer = VideoComposer()

    print("Fetching Quran sequence...")
    # Surah 112 (Al-Ikhlas) or 108 (Al-Kawthar) for a fast test run
    q_data = qs.select_ayah_sequence(surah_number=112, start_ayah=1)
    print(f"Selected: Surah {q_data['surah_name_en']} ({q_data['total_duration']:.1f}s)")

    print("Fetching airplane footage...")
    v_path = vs.get_airplane_video()
    print("Airplane video:", v_path)

    print("Composing 9:16 vertical reel...")
    out_mp4 = composer.compose_reel(v_path, q_data)
    print("Finished Reel successfully:", out_mp4)
