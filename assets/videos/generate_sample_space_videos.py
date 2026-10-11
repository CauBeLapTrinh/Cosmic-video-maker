"""
Generates sample local cosmic videos for assets/videos/.
Provides immediate offline stock video clips for users without API keys.
"""

import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from modules.visuals import apply_ken_burns_to_image


def generate_starfield_flight_video(output_path: str, duration: float = 8.0, width: int = 1920, height: int = 1080):
    """Generates a 3D starfield warp flight video."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    temp_img = output_path.replace(".mp4", "_base.png")

    img = Image.new("RGB", (width, height), (3, 5, 12))
    draw = ImageDraw.Draw(img)

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([width*0.2, height*0.2, width*0.8, height*0.8], fill=(15, 30, 80, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=80))
    img.paste(glow, (0, 0), glow)

    np.random.seed(101)
    for _ in range(1200):
        x = np.random.randint(0, width)
        y = np.random.randint(0, height)
        b = np.random.randint(160, 255)
        color = (b, b, b) if np.random.rand() > 0.3 else (b - 30, b - 10, b)
        sz = 1 if np.random.rand() > 0.1 else 2
        draw.ellipse([x - sz, y - sz, x + sz, y + sz], fill=color)

    img.save(temp_img)
    apply_ken_burns_to_image(temp_img, output_path, duration=duration, width=width, height=height, motion_type="zoom_in")
    if os.path.exists(temp_img):
        os.remove(temp_img)
    return output_path


def generate_nebula_drift_video(output_path: str, duration: float = 8.0, width: int = 1920, height: int = 1080):
    """Generates a luminous purple & cyan cosmic nebula video."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    temp_img = output_path.replace(".mp4", "_base.png")

    img = Image.new("RGB", (width, height), (5, 6, 18))
    draw = ImageDraw.Draw(img)

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([width*0.1, height*0.1, width*0.6, height*0.9], fill=(70, 20, 100, 140))
    gdraw.ellipse([width*0.4, height*0.15, width*0.9, height*0.95], fill=(15, 75, 120, 130))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=80))
    img.paste(glow, (0, 0), glow)

    np.random.seed(202)
    for _ in range(1100):
        x = np.random.randint(0, width)
        y = np.random.randint(0, height)
        b = np.random.randint(180, 255)
        draw.point((x, y), fill=(b, b, b))

    img.save(temp_img)
    apply_ken_burns_to_image(temp_img, output_path, duration=duration, width=width, height=height, motion_type="zoom_out")
    if os.path.exists(temp_img):
        os.remove(temp_img)
    return output_path


def generate_black_hole_vortex_video(output_path: str, duration: float = 8.0, width: int = 1920, height: int = 1080):
    """Generates an ominous gravitational accretion disk video."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    temp_img = output_path.replace(".mp4", "_base.png")

    img = Image.new("RGB", (width, height), (2, 2, 6))
    draw = ImageDraw.Draw(img)

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    cx, cy = width // 2, height // 2
    gdraw.ellipse([cx - 450, cy - 220, cx + 450, cy + 220], fill=(240, 140, 20, 160))
    gdraw.ellipse([cx - 300, cy - 140, cx + 300, cy + 140], fill=(255, 220, 100, 220))
    gdraw.ellipse([cx - 180, cy - 180, cx + 180, cy + 180], fill=(0, 0, 0, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=25))
    img.paste(glow, (0, 0), glow)

    draw.ellipse([cx - 160, cy - 160, cx + 160, cy + 160], fill=(1, 1, 2))

    np.random.seed(303)
    for _ in range(800):
        x = np.random.randint(0, width)
        y = np.random.randint(0, height)
        if (x - cx)**2 + (y - cy)**2 > 200**2:
            b = np.random.randint(150, 255)
            draw.point((x, y), fill=(b, b, b))

    img.save(temp_img)
    apply_ken_burns_to_image(temp_img, output_path, duration=duration, width=width, height=height, motion_type="zoom_in")
    if os.path.exists(temp_img):
        os.remove(temp_img)
    return output_path


if __name__ == "__main__":
    v1 = generate_starfield_flight_video("assets/videos/starfield_warp.mp4", duration=10.0)
    v2 = generate_nebula_drift_video("assets/videos/cosmic_nebula_drift.mp4", duration=10.0)
    v3 = generate_black_hole_vortex_video("assets/videos/black_hole_vortex.mp4", duration=10.0)
    print(f"Generated sample local cosmic videos successfully: {v1}, {v2}, {v3}")
