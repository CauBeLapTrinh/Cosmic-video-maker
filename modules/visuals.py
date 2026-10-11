"""
Module 3: Visuals Fetcher & Processor
Fetches HD stock video footage or images from Pixabay API (and legacy Pexels API),
provides seamless fallback to local video assets in assets/videos/,
generates procedural high-res cosmic starfields/nebulae as offline fallbacks,
and applies cinematic Ken Burns motion effects (zoom/pan) to static assets.
"""

import os
import glob
import random
import requests
import subprocess
from typing import Optional, Dict, Any, List
from PIL import Image, ImageDraw, ImageFilter
import numpy as np


# ==========================================
# 1. PIXABAY STOCK API (Videos & Photos)
# ==========================================

def search_pixabay_video(
    query: str,
    api_key: str,
    orientation: str = "all"  # "all", "horizontal", "vertical"
) -> Optional[str]:
    """
    Searches Pixabay Video API and returns the direct HD MP4 download URL.
    Pixabay API Docs: https://pixabay.com/api/docs/#api_videos
    """
    if not api_key:
        return None

    url = "https://pixabay.com/api/videos/"
    # Pixabay query terms should be space-separated simple words
    clean_query = " ".join([w for w in query.replace(",", " ").split() if len(w) > 2][:3])
    if not clean_query:
        clean_query = "space galaxy"

    params = {
        "key": api_key,
        "q": clean_query,
        "video_type": "all",
        "per_page": 8,
        "safesearch": "true"
    }

    try:
        resp = requests.get(url, params=params, timeout=12)
        if resp.status_code != 200:
            print(f"[Pixabay Video] Status {resp.status_code}: {resp.text[:120]}")
            return None
        data = resp.json()
        hits = data.get("hits", [])
        if not hits:
            # Retry with broader cosmic keyword
            if clean_query != "space universe":
                params["q"] = "space universe"
                r2 = requests.get(url, params=params, timeout=10)
                if r2.status_code == 200:
                    hits = r2.json().get("hits", [])

        if not hits:
            return None

        # Select first hit with valid MP4 video link
        for hit in hits:
            v_dict = hit.get("videos", {})
            # Prefer large (1080p), then medium (720p), then small
            for res_key in ["large", "medium", "small"]:
                target_video = v_dict.get(res_key, {})
                v_url = target_video.get("url")
                if v_url:
                    return v_url

    except Exception as e:
        print(f"[Pixabay Video] Request error for query '{query}': {e}")

    return None


def search_pixabay_photo(
    query: str,
    api_key: str,
    orientation: str = "horizontal"
) -> Optional[str]:
    """
    Searches Pixabay Photo API and returns high-resolution image URL.
    """
    if not api_key:
        return None

    url = "https://pixabay.com/api/"
    clean_query = " ".join([w for w in query.replace(",", " ").split() if len(w) > 2][:3])
    if not clean_query:
        clean_query = "space stars"

    params = {
        "key": api_key,
        "q": clean_query,
        "image_type": "photo",
        "orientation": "vertical" if orientation == "vertical" else "horizontal",
        "per_page": 8,
        "safesearch": "true"
    }

    try:
        resp = requests.get(url, params=params, timeout=12)
        if resp.status_code != 200:
            return None
        data = resp.json()
        hits = data.get("hits", [])
        if not hits:
            return None

        # Pick high resolution photo
        first = hits[0]
        return first.get("largeImageURL") or first.get("webformatURL")
    except Exception as e:
        print(f"[Pixabay Photo] Request error for query '{query}': {e}")
        return None


# ==========================================
# 2. PEXELS API (LEGACY SUPPORT)
# ==========================================

def search_pexels_video(
    query: str,
    api_key: str,
    orientation: str = "landscape"
) -> Optional[str]:
    """Legacy Pexels Video API search."""
    if not api_key:
        return None
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "orientation": orientation, "per_page": 5}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=12)
        if resp.status_code != 200:
            return None
        videos = resp.json().get("videos", [])
        for v in videos:
            files = v.get("video_files", [])
            hd_files = [f for f in files if f.get("file_type") == "video/mp4" and (f.get("height", 0) >= 720 or f.get("width", 0) >= 720)]
            if hd_files:
                hd_files.sort(key=lambda x: abs(x.get("height", 0) - 1080))
                return hd_files[0]["link"]
            elif files:
                return files[0]["link"]
    except Exception:
        pass
    return None


def search_pexels_photo(
    query: str,
    api_key: str,
    orientation: str = "landscape"
) -> Optional[str]:
    """Legacy Pexels Photo API search."""
    if not api_key:
        return None
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "orientation": orientation, "per_page": 5}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=12)
        if resp.status_code != 200:
            return None
        photos = resp.json().get("photos", [])
        if photos:
            src = photos[0].get("src", {})
            return src.get("large2x") or src.get("original") or src.get("large")
    except Exception:
        pass
    return None


# ==========================================
# 3. LOCAL VIDEO ASSET LIBRARY
# ==========================================

def get_local_video_from_assets(
    query: str,
    scene_id: int,
    assets_dir: str = "assets/videos"
) -> Optional[str]:
    """
    Finds a matching local video from assets/videos/ based on keyword matching.
    If no keyword matches, picks deterministically by scene_id to ensure variety.
    """
    if not os.path.exists(assets_dir):
        return None

    video_extensions = ("*.mp4", "*.mov", "*.mkv", "*.webm", "*.avi")
    files: List[str] = []
    for ext in video_extensions:
        files.extend(glob.glob(os.path.join(assets_dir, ext)))

    if not files:
        return None

    # Check for keyword matches in filename
    query_words = [w.lower() for w in query.replace("_", " ").replace("-", " ").split() if len(w) > 2]
    for f in files:
        base_name = os.path.basename(f).lower()
        for qw in query_words:
            if qw in base_name:
                return f

    # Deterministic fallback by scene_id
    selected_idx = (scene_id - 1) % len(files)
    return files[selected_idx]


def list_local_videos(assets_dir: str = "assets/videos") -> List[str]:
    """Returns all available video files in the local video library."""
    if not os.path.exists(assets_dir):
        return []
    video_extensions = ("*.mp4", "*.mov", "*.mkv", "*.webm", "*.avi")
    files: List[str] = []
    for ext in video_extensions:
        files.extend(glob.glob(os.path.join(assets_dir, ext)))
    return files


# ==========================================
# 4. DOWNLOAD & PROCESSING UTILITIES
# ==========================================

def download_file(url: str, output_path: str) -> bool:
    """Downloads an external URL to a local file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"[Download Error] Failed to download {url}: {e}")
        return False


def generate_procedural_cosmic_image(
    width: int,
    height: int,
    output_path: str,
    scene_heading: str = "Deep Space",
    color_palette: str = "deep_space"
) -> str:
    """
    Generates a high-resolution procedural celestial artwork.
    Used as an offline fallback or backdrop generator.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    img = Image.new("RGBA", (width, height), (6, 8, 16, 255))

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    center_x = random.randint(int(width * 0.3), int(width * 0.7))
    center_y = random.randint(int(height * 0.3), int(height * 0.7))
    
    if color_palette == "deep_space":
        glow_colors = [(30, 20, 60, 140), (15, 45, 90, 110), (5, 15, 35, 0)]
    elif color_palette == "nebula_cyan":
        glow_colors = [(10, 60, 90, 150), (15, 30, 75, 100), (4, 10, 25, 0)]
    elif color_palette == "solar_gold":
        glow_colors = [(80, 45, 10, 150), (40, 20, 10, 100), (10, 5, 10, 0)]
    else:
        glow_colors = [(55, 15, 75, 150), (25, 10, 50, 100), (8, 4, 20, 0)]

    max_rad = max(width, height) // 2
    for r in range(max_rad, 0, -20):
        ratio = r / max_rad
        c_idx = min(len(glow_colors) - 1, int((1 - ratio) * (len(glow_colors) - 1)))
        c = glow_colors[c_idx]
        glow_draw.ellipse(
            [center_x - r, center_y - r, center_x + r, center_y + r],
            fill=c
        )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=40))
    img = Image.alpha_composite(img, glow)

    stars_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    stars_draw = ImageDraw.Draw(stars_layer)
    
    num_stars = int(width * height * 0.00035)
    for _ in range(num_stars):
        sx = random.randint(0, width - 1)
        sy = random.randint(0, height - 1)
        brightness = random.randint(140, 255)
        tint = random.choice([
            (brightness, brightness, brightness, 255),
            (brightness - 20, brightness - 10, brightness, 255),
            (brightness, brightness - 15, brightness - 40, 255)
        ])
        size = random.choices([1, 2, 3], weights=[85, 12, 3])[0]
        if size == 1:
            stars_draw.point((sx, sy), fill=tint)
        elif size == 2:
            stars_draw.ellipse([sx - 1, sy - 1, sx + 1, sy + 1], fill=tint)
        else:
            stars_draw.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=tint)
            stars_draw.line([sx - 6, sy, sx + 6, sy], fill=(brightness, brightness, brightness, 180), width=1)
            stars_draw.line([sx, sy - 6, sx, sy + 6], fill=(brightness, brightness, brightness, 180), width=1)

    img = Image.alpha_composite(img, stars_layer)
    final_img = img.convert("RGB")
    final_img.save(output_path, quality=95)
    return output_path


def apply_ken_burns_to_image(
    image_path: str,
    output_mp4_path: str,
    duration: float,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    motion_type: str = "zoom_in"
) -> str:
    """
    Applies cinematic Ken Burns camera movement to a static image,
    exporting a clean 30fps H.264 video.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4_path)), exist_ok=True)
    frames = int(duration * fps)

    if motion_type == "zoom_out":
        zoom_expr = "max(1.15-0.0012*on,1.0)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif motion_type == "pan_left":
        zoom_expr = "1.12"
        x_expr = "(1-on/d)*(iw-iw/zoom)"
        y_expr = "ih/2-(ih/zoom/2)"
    else:  # default "zoom_in"
        zoom_expr = "min(zoom+0.0012,1.15)"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"

    filter_complex = f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,crop={width*2}:{height*2},zoompan=z='{zoom_expr}':d={frames}:x='{x_expr}':y='{y_expr}':s={width}x{height}:fps={fps}"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", filter_complex,
        "-t", f"{duration:.2f}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "faster",
        "-r", str(fps),
        output_mp4_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        cmd_fallback = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
            "-t", f"{duration:.2f}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            output_mp4_path
        ]
        subprocess.run(cmd_fallback, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return output_mp4_path


def normalize_video_clip(
    video_path: str,
    output_mp4_path: str,
    target_duration: float,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30
) -> str:
    """Standardizes any video to match aspect ratio, duration, and 30fps."""
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4_path)), exist_ok=True)
    
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps}"

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", video_path,
        "-vf", vf,
        "-t", f"{target_duration:.2f}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-an",
        "-preset", "faster",
        output_mp4_path
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_mp4_path


# ==========================================
# 5. MASTER SCENE VISUAL ORCHESTRATOR
# ==========================================

def fetch_or_generate_scene_visual(
    scene_id: int,
    query: str,
    pixabay_key: Optional[str] = None,
    pexels_key: Optional[str] = None,
    aspect_ratio: str = "16:9",
    target_duration: float = 8.0,
    output_video_path: str = "output/scene_1.mp4",
    output_image_path: str = "output/scene_1.png",
    custom_asset_path: Optional[str] = None,
    preferred_source: str = "auto"  # "auto", "pixabay", "local", "pexels", "procedural"
) -> str:
    """
    Master pipeline for fetching or creating a scene's visual clip:
    1. Custom Asset (User upload) takes highest precedence.
    2. Preferred Source logic:
       - If 'pixabay': searches Pixabay Videos / Photos.
       - If 'local': fetches from assets/videos/.
       - If 'pexels': searches Pexels.
       - If 'procedural': generates celestial canvas.
       - If 'auto': checks Pixabay -> Pexels -> Local Assets -> Procedural.
    """
    is_vertical = ("9:16" in aspect_ratio)
    width = 1080 if is_vertical else 1920
    height = 1920 if is_vertical else 1080
    orientation = "vertical" if is_vertical else "horizontal"

    motions = ["zoom_in", "zoom_out", "pan_left"]
    motion = motions[(scene_id - 1) % len(motions)]

    # 1. Custom Asset Check (Highest Priority)
    if custom_asset_path and os.path.exists(custom_asset_path):
        ext = os.path.splitext(custom_asset_path)[1].lower()
        if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            return normalize_video_clip(custom_asset_path, output_video_path, target_duration, width, height)
        elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
            return apply_ken_burns_to_image(custom_asset_path, output_video_path, target_duration, width, height, motion_type=motion)

    # 2. Local Asset Library Check (if preferred or no keys)
    if preferred_source == "local":
        local_vid = get_local_video_from_assets(query, scene_id)
        if local_vid:
            return normalize_video_clip(local_vid, output_video_path, target_duration, width, height)

    # 3. Pixabay API Search (Primary Stock Engine)
    if pixabay_key and preferred_source in ["auto", "pixabay"]:
        vid_url = search_pixabay_video(query, pixabay_key, orientation=orientation)
        if vid_url:
            raw_tmp = output_video_path.replace(".mp4", "_raw.mp4")
            if download_file(vid_url, raw_tmp):
                processed = normalize_video_clip(raw_tmp, output_video_path, target_duration, width, height)
                if os.path.exists(raw_tmp):
                    try:
                        os.remove(raw_tmp)
                    except Exception:
                        pass
                return processed

        # Pixabay Photo + Ken Burns
        photo_url = search_pixabay_photo(query, pixabay_key, orientation=orientation)
        if photo_url:
            if download_file(photo_url, output_image_path):
                return apply_ken_burns_to_image(output_image_path, output_video_path, target_duration, width, height, motion_type=motion)

    # 4. Pexels API (Legacy)
    if pexels_key and preferred_source in ["auto", "pexels"]:
        video_url = search_pexels_video(query, pexels_key, orientation="portrait" if is_vertical else "landscape")
        if video_url:
            raw_tmp = output_video_path.replace(".mp4", "_raw.mp4")
            if download_file(video_url, raw_tmp):
                processed = normalize_video_clip(raw_tmp, output_video_path, target_duration, width, height)
                if os.path.exists(raw_tmp):
                    try:
                        os.remove(raw_tmp)
                    except Exception:
                        pass
                return processed

        photo_url = search_pexels_photo(query, pexels_key, orientation="portrait" if is_vertical else "landscape")
        if photo_url:
            if download_file(photo_url, output_image_path):
                return apply_ken_burns_to_image(output_image_path, output_video_path, target_duration, width, height, motion_type=motion)

    # 5. Local Assets Fallback (Checks assets/videos/ before procedural)
    local_vid = get_local_video_from_assets(query, scene_id)
    if local_vid:
        return normalize_video_clip(local_vid, output_video_path, target_duration, width, height)

    # 6. Procedural Deep-Space Generation Fallback
    palettes = ["deep_space", "nebula_cyan", "violet", "solar_gold"]
    palette = palettes[(scene_id - 1) % len(palettes)]
    generate_procedural_cosmic_image(width, height, output_image_path, color_palette=palette)
    return apply_ken_burns_to_image(output_image_path, output_video_path, target_duration, width, height, motion_type=motion)
