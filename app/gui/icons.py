import math
from pathlib import Path
from typing import Optional, Tuple, Dict
from PIL import Image, ImageDraw
import customtkinter as ctk

ROOT = Path(__file__).resolve().parents[2]
ICONS_DIR = ROOT / "assets" / "icons"

_IMAGE_CACHE: Dict[Tuple[str, int, int], ctk.CTkImage] = {}

def _draw_dashboard(draw: ImageDraw.ImageDraw, color: Tuple[int, int, int, int]):
    w = 16
    r = 14
    draw.rounded_rectangle([36, 36, 114, 136], radius=r, outline=color, width=w)
    draw.rounded_rectangle([36, 156, 114, 220], radius=r, outline=color, width=w)
    draw.rounded_rectangle([134, 36, 220, 100], radius=r, outline=color, width=w)
    draw.rounded_rectangle([134, 120, 220, 220], radius=r, outline=color, width=w)

def _draw_gestures(draw: ImageDraw.ImageDraw, color: Tuple[int, int, int, int]):
    w = 16
    draw.rounded_rectangle([80, 124, 176, 216], radius=24, outline=color, width=w)
    draw.rounded_rectangle([52, 140, 84, 196], radius=16, outline=color, width=w)
    draw.rounded_rectangle([80, 44, 104, 134], radius=12, outline=color, width=w)
    draw.rounded_rectangle([108, 32, 132, 134], radius=12, outline=color, width=w)
    draw.rounded_rectangle([136, 44, 160, 134], radius=12, outline=color, width=w)
    draw.rounded_rectangle([164, 76, 188, 134], radius=12, outline=color, width=w)

def _draw_profiles(draw: ImageDraw.ImageDraw, color: Tuple[int, int, int, int]):
    w = 16
    draw.ellipse([88, 36, 168, 116], outline=color, width=w)
    draw.arc([44, 136, 212, 276], start=180, end=360, fill=color, width=w)
    draw.line([(44, 206), (44, 220)], fill=color, width=w)
    draw.line([(212, 206), (212, 220)], fill=color, width=w)
    draw.line([(44, 220), (212, 220)], fill=color, width=w)

def _draw_obs(draw: ImageDraw.ImageDraw, color: Tuple[int, int, int, int]):
    w = 16
    draw.rounded_rectangle([36, 44, 220, 172], radius=16, outline=color, width=w)
    draw.line([(128, 172), (128, 208)], fill=color, width=w)
    draw.line([(88, 208), (168, 208)], fill=color, width=w)
    draw.polygon([(112, 84), (156, 108), (112, 132)], fill=color)

def _draw_camera(draw: ImageDraw.ImageDraw, color: Tuple[int, int, int, int]):
    w = 16
    draw.rounded_rectangle([36, 76, 220, 204], radius=18, outline=color, width=w)
    draw.rounded_rectangle([84, 46, 136, 76], radius=8, outline=color, width=w)
    draw.ellipse([90, 102, 166, 178], outline=color, width=w)
    draw.ellipse([116, 128, 140, 152], fill=color)

def _draw_calibration(draw: ImageDraw.ImageDraw, color: Tuple[int, int, int, int]):
    w = 16
    draw.ellipse([54, 54, 202, 202], outline=color, width=w)
    draw.ellipse([96, 96, 160, 160], outline=color, width=w)
    draw.ellipse([120, 120, 136, 136], fill=color)
    draw.line([(128, 24), (128, 54)], fill=color, width=w)
    draw.line([(128, 202), (128, 232)], fill=color, width=w)
    draw.line([(24, 128), (54, 128)], fill=color, width=w)
    draw.line([(202, 128), (232, 128)], fill=color, width=w)

def _draw_logs(draw: ImageDraw.ImageDraw, color: Tuple[int, int, int, int]):
    w = 16
    draw.rounded_rectangle([36, 44, 220, 212], radius=18, outline=color, width=w)
    draw.line([(68, 100), (96, 124)], fill=color, width=w)
    draw.line([(96, 124), (68, 148)], fill=color, width=w)
    draw.line([(116, 148), (160, 148)], fill=color, width=w)
    draw.line([(68, 180), (188, 180)], fill=color, width=12)

def _draw_settings(draw: ImageDraw.ImageDraw, color: Tuple[int, int, int, int]):
    center = 128
    r_outer = 94
    r_body = 76
    r_hole = 30
    teeth = 8
    for i in range(teeth):
        ang = (2 * math.pi / teeth) * i
        x1 = center + (r_outer - 4) * math.cos(ang)
        y1 = center + (r_outer - 4) * math.sin(ang)
        draw.line([(center + 50 * math.cos(ang), center + 50 * math.sin(ang)), (x1, y1)], fill=color, width=28)
    draw.ellipse([center - r_body, center - r_body, center + r_body, center + r_body], fill=color)
    draw.ellipse([center - r_hole, center - r_hole, center + r_hole, center + r_hole], fill=(0, 0, 0, 0))

def _draw_logo(draw: ImageDraw.ImageDraw, color: Tuple[int, int, int, int]):
    w = 16
    draw.rounded_rectangle([36, 36, 220, 220], radius=32, outline=color, width=w)
    draw.arc([64, 64, 192, 192], start=210, end=330, fill=color, width=w)
    draw.arc([88, 88, 168, 168], start=210, end=330, fill=color, width=w)
    draw.ellipse([116, 140, 140, 164], fill=color)
    draw.line([(128, 164), (128, 196)], fill=color, width=w)

_ICON_GENERATORS = {
    "dashboard": _draw_dashboard,
    "gestures": _draw_gestures,
    "profiles": _draw_profiles,
    "obs": _draw_obs,
    "camera": _draw_camera,
    "calibration": _draw_calibration,
    "logs": _draw_logs,
    "settings": _draw_settings,
    "logo": _draw_logo,
}

def ensure_icons_exist():
    """Gera arquivos de ícones PNG em assets/icons se não existirem."""
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    themes = [
        ("dark", (245, 247, 250, 255)),
        ("light", (44, 62, 80, 255)),
    ]
    for name, draw_fn in _ICON_GENERATORS.items():
        for theme_name, color in themes:
            out_file = ICONS_DIR / f"{name}_{theme_name}.png"
            if not out_file.exists():
                canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
                draw = ImageDraw.Draw(canvas)
                draw_fn(draw, color)
                # Anti-aliasing com supersampling LANCZOS
                res = canvas.resize((64, 64), Image.Resampling.LANCZOS)
                res.save(out_file)

def get_icon(name: str, size: Tuple[int, int] = (20, 20)) -> Optional[ctk.CTkImage]:
    """Retorna uma instância em cache de CTkImage para o ícone formal solicitado."""
    cache_key = (name, size[0], size[1])
    if cache_key in _IMAGE_CACHE:
        return _IMAGE_CACHE[cache_key]

    ensure_icons_exist()
    dark_path = ICONS_DIR / f"{name}_dark.png"
    light_path = ICONS_DIR / f"{name}_light.png"

    if dark_path.exists() and light_path.exists():
        try:
            dark_img = Image.open(dark_path)
            light_img = Image.open(light_path)
            ctk_img = ctk.CTkImage(light_image=light_img, dark_image=dark_img, size=size)
            _IMAGE_CACHE[cache_key] = ctk_img
            return ctk_img
        except Exception:
            return None
    return None
