# 🌌 Cosmic Video Maker

> **Automated Faceless YouTube & Shorts Video Generation Platform for Cosmic Mysteries, Astrophysics, and "What-If" Scenarios.**

An end-to-end local web application built with **Streamlit**, **Python**, **Edge-TTS**, **Google Gemini**, and **FFmpeg** that automates the entire multimedia pipeline: from dramatic scriptwriting and scene planning to neural voiceovers, dynamic stock video fetching, Ken Burns visual animation, audio ducking, synchronized subtitle burning, and final MP4 rendering.

---

## 🌟 Key Features

- **🚀 Step-by-Step Production Dashboard**: A tailored dark-mode Streamlit UI with cosmic aesthetic, interactive editable scene table, duration presets, and live progress bars.
- **📜 Long-Form & Shorts Script Generator**:
  - Dynamically calculates target word count and scene count:
    - **Long-form (3-5 mins)**: 16-24 scenes (~550-750 words).
    - **Medium (2-3 mins)**: 10-14 scenes (~350-450 words).
    - **Shorts (60s)**: 4-6 scenes (~120-150 words).
    - **Custom Scene Count**: 5 to 30 scenes with advanced slider.
  - Enforces rigid JSON schema validation and retry logic with Google Gemini and OpenAI.
  - Includes full 18-scene offline documentary templates for zero-API usage.
- **🎙️ Scene-by-Scene Audio Architecture (Zero Render Cutoffs)**:
  - Generates individual `.mp3` voiceover clips for **EACH individual scene** using `edge-tts`.
  - Measures the **exact duration (in seconds)** of each scene's audio.
  - Forces each scene's visual clip to strictly match its exact scene audio duration.
  - Eliminates premature render ending: video duration matches audio duration down to the millisecond!
- **🎵 Cosmic Ambient Audio & Ducking**:
  - Built-in atmospheric space synth pads and deep space drone tracks.
  - Dynamic volume ducking (-22 dB = ~12% volume) with a 3.0s smooth outro fade.
- **🎬 Multi-Source Visual Pipeline**:
  - **Option A (Pixabay API)**: Auto-searches and downloads 1080p cosmic footage & photos via the free **Pixabay API**.
  - **Option B (Local Video Library `assets/videos/`)**: Seamlessly loops and trims local space video clips to exact scene audio durations.
  - **Option C (Procedural Cosmic Art & AI Custom Uploads)**: High-res starry nebulae generated procedurally, or drag-and-drop replacement with custom ComfyUI / Stable Diffusion renders.
  - **Ken Burns Motion Engine**: Smooth 30fps zooms and pans for static images strictly matching scene audio duration.
- **💬 Broadcast-Grade Subtitle Burning**:
  - Generates styled `.ass` and `.srt` subtitles with high-contrast colors (Cyber Yellow, Neon Cyan, Classic White) and bold drop shadows.
  - Automatically burned into the final MP4 using `FFmpeg libass` without Windows path conflicts.
- **📐 Dual Aspect Ratio**:
  - **16:9 Landscape (1920x1080)** at 4000 kbps for standard YouTube long-form documentaries.
  - **9:16 Portrait (1080x1920)** for YouTube Shorts, Instagram Reels, and TikTok.

---

## 📂 Project Structure

```
Cosmic-video-maker/
├── modules/
│   ├── __init__.py
│   ├── script_gen.py         # AI script, scenes & prompts (Gemini, OpenAI, Offline)
│   ├── audio_gen.py          # Edge-TTS synthesis, timestamp extraction & BGM ducking
│   ├── visuals.py            # Pixabay & Pexels fetcher, local video library & Ken Burns
│   └── video_composer.py     # FFmpeg composition, concatenation, subtitle burning & export
├── assets/
│   ├── bgm/                  # Ambient cosmic audio tracks (deep space drone, nebula)
│   │   └── generate_bgm.py   # Procedural synth pad generator
│   ├── videos/               # Local cosmic video library (starfield warp, nebula, black hole)
│   └── sample_visuals/       # Sample background assets
├── output/                   # Rendered MP4 videos, audio tracks, and subtitles
├── app.py                    # Streamlit Dashboard UI
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── run_app.bat               # One-click Windows launcher
└── README.md                 # Documentation
```

---

## 🛠️ Prerequisites & Installation

### 1. Python
Ensure you have **Python 3.10+** (Python 3.11 or 3.12 recommended) installed:
```bash
python --version
```

### 2. FFmpeg (Required for video compositing)
FFmpeg with `libass` and `libx264` must be installed and accessible in your system's PATH.

- **Windows (Recommended via Winget)**:
  ```powershell
  winget install Gyan.FFmpeg
  ```
  *Or download from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) and add `bin` to your System PATH.*

- **macOS**:
  ```bash
  brew install ffmpeg
  ```

- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```

Verify FFmpeg is recognized:
```bash
ffmpeg -version
```

### 3. Clone / Open Project & Install Dependencies
Navigate to the project root directory and create a virtual environment:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🔑 Configuration (.env)

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your keys (optional, you can also enter them directly in the Streamlit UI sidebar):
```env
# Google Gemini API Key (Get free at https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here

# OpenAI API Key (Optional)
OPENAI_API_KEY=your_openai_api_key_here

# Pixabay API Key (Free instant key at https://pixabay.com/api/docs/)
PIXABAY_API_KEY=your_pixabay_api_key_here

# Pexels API Key (Optional / Legacy)
PEXELS_API_KEY=your_pexels_api_key_here
```

> **Note:** If you don't supply any API keys, the application automatically uses its **built-in Curated Cosmic Generator**, **Local Video Library (`assets/videos/`)**, and **Procedural Celestial Visual Engine**, making it 100% operational offline!

---

## 🚀 Running the Web Application

### Option A: Windows One-Click Launcher
Double-click `run_app.bat` in the project directory.

### Option B: Terminal Command
```bash
streamlit run app.py
```
Your default web browser will automatically open:
```
Local URL: http://localhost:8501
```

---

## 🧭 Step-by-Step User Workflow

1. **Sidebar Configuration**:
   - Set your **Aspect Ratio** (`16:9` for long-form or `9:16` for Shorts).
   - Select your preferred **Voice** (e.g. `Christopher (US Male - Deep Documentary)`) and test it with the `Preview Voice` button.
   - Choose a cosmic **Background Music** loop and adjust the ducking level (-22 dB recommended).
   - Pick your **Subtitle Style** (Cyber Yellow, Neon Cyan, Classic White).

2. **Step 1: Script & Scene Breakdown**:
   - Pick a curated cosmic scenario (e.g., *"What if the Moon vanished tomorrow?"*, *"What if a Black Hole entered our Solar System?"*) or type a custom topic.
   - Click **Generate Cosmic Script**.
   - Review and fine-tune each scene's narration, visual prompt, and Pexels stock keyword.

3. **Step 2: Voiceover & Subtitles**:
   - Click **Generate Voiceover & Subtitles**.
   - Listen to the high-clarity narration mixed with atmospheric music.
   - Inspect the synchronized subtitle cues.

4. **Step 3: Visual Assets Studio**:
   - Click **Auto-Fetch All Visuals**. The app will automatically pull matching 1080p clips from Pexels, or generate starry procedural visuals with Ken Burns motion.
   - Drag and drop any custom AI images or videos (from ComfyUI, Midjourney, etc.) to replace any individual scene asset.

5. **Step 4: Video Assembly & Rendering**:
   - Click **Render Final Cosmic Video**.
   - Watch the real-time progress bar as FFmpeg concatenates scene clips, mixes audio, and burns the stylized subtitles.

6. **Step 5: Player & Export**:
   - Watch the finished video directly in the integrated player.
   - Click **Download Final MP4 Video**.
   - Copy the ready-made Title, YouTube Description, and Hashtags.

---

## 📄 License
MIT License. Built for creators, astronomers, and cosmic storytellers.
