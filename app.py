"""
Cosmic Video Maker - Streamlit Dashboard
Automates the creation of faceless YouTube long-form videos (3-5 minutes) and Shorts
in the "Cosmic Mysteries & What-If Scenarios" niche.
"""

import os
import time
from typing import Dict, Any, List
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Import internal modules
from modules.script_gen import (
    generate_script,
    calculate_target_metrics,
    CosmicScript,
    Scene,
    OFFLINE_PRESETS
)
from modules.audio_gen import (
    VOICE_PRESETS,
    generate_all_scenes_audio,
    generate_voiceover_sync,
    build_chunked_subtitles,
    write_ass_file,
    write_srt_file,
    mix_voice_and_bgm,
    get_audio_duration
)
from modules.visuals import (
    fetch_or_generate_scene_visual,
    generate_procedural_cosmic_image,
    apply_ken_burns_to_image,
    list_local_videos,
    get_local_video_from_assets
)
from modules.video_composer import (
    render_final_video,
    get_video_info
)

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Cosmic Video Maker | Long-Form AI Studio",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Cosmic Dark Aesthetic CSS
st.markdown("""
<style>
    /* Global Background & Typography */
    .stApp {
        background: radial-gradient(circle at 50% 10%, #0d122b 0%, #060914 70%, #02040a 100%);
        color: #e0e6ed;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Cosmic Header Banner */
    .cosmic-header {
        background: linear-gradient(135deg, rgba(28, 38, 77, 0.7) 0%, rgba(13, 18, 43, 0.9) 100%);
        border: 1px solid rgba(80, 140, 255, 0.25);
        border-radius: 14px;
        padding: 22px 28px;
        margin-bottom: 22px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45);
        backdrop-filter: blur(8px);
    }
    .cosmic-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #60a5fa, #a78bfa, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }
    .cosmic-subtitle {
        color: #94a3b8;
        font-size: 0.98rem;
    }

    /* Cards */
    .scene-card {
        background: rgba(15, 23, 42, 0.65);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    }
    .scene-badge {
        display: inline-block;
        padding: 3px 10px;
        background: rgba(99, 102, 241, 0.2);
        border: 1px solid rgba(99, 102, 241, 0.4);
        color: #a5b4fc;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 8px;
    }

    /* Button Enhancements */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "script" not in st.session_state:
    st.session_state.script = None
if "audio_manifest" not in st.session_state:
    st.session_state.audio_manifest = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "subtitles_path" not in st.session_state:
    st.session_state.subtitles_path = None
if "subtitle_cues" not in st.session_state:
    st.session_state.subtitle_cues = []
if "total_duration" not in st.session_state:
    st.session_state.total_duration = 0.0
if "scene_clips" not in st.session_state:
    st.session_state.scene_clips = {}
if "scene_images" not in st.session_state:
    st.session_state.scene_images = {}
if "final_video_path" not in st.session_state:
    st.session_state.final_video_path = None
if "video_info" not in st.session_state:
    st.session_state.video_info = {}


# --- SIDEBAR: Configuration & Settings ---
with st.sidebar:
    st.markdown("### ⚙️ Studio Settings")
    
    with st.expander("🔑 API Credentials", expanded=False):
        gemini_key_env = os.getenv("GEMINI_API_KEY", "")
        openai_key_env = os.getenv("OPENAI_API_KEY", "")
        pixabay_key_env = os.getenv("PIXABAY_API_KEY", "")
        pexels_key_env = os.getenv("PEXELS_API_KEY", "")

        gemini_api_key = st.text_input("Gemini API Key", value=gemini_key_env, type="password", help="Get free key at https://aistudio.google.com/")
        openai_api_key = st.text_input("OpenAI API Key (Optional)", value=openai_key_env, type="password")
        pixabay_api_key = st.text_input("Pixabay API Key", value=pixabay_key_env, type="password", help="Get free instant key at https://pixabay.com/api/docs/")
        pexels_api_key = st.text_input("Pexels API Key (Optional/Legacy)", value=pexels_key_env, type="password")
        
        # Status indicators
        if gemini_api_key or openai_api_key:
            st.success("AI Script Generation: Active")
        else:
            st.info("Using Built-in Curated Cosmic Generator")
            
        if pixabay_api_key:
            st.success("Pixabay 1080p Stock Engine: Active")
        elif pexels_api_key:
            st.success("Pexels Stock Engine: Active")

        local_vids_count = len(list_local_videos())
        st.success(f"Local Video Library: Active ({local_vids_count} clips in assets/videos/)")

    st.markdown("---")
    st.markdown("### 🎥 Visuals Engine")
    visual_source_label = st.selectbox(
        "Stock Footage Source",
        [
            "Auto (Pixabay -> Local Assets -> Procedural)",
            "Pixabay Stock Footage API",
            "Local Video Library (assets/videos/)",
            "Procedural Cosmic Art Generator",
            "Pexels API (Legacy)"
        ],
        index=0
    )
    visual_source_map = {
        "Auto (Pixabay -> Local Assets -> Procedural)": "auto",
        "Pixabay Stock Footage API": "pixabay",
        "Local Video Library (assets/videos/)": "local",
        "Procedural Cosmic Art Generator": "procedural",
        "Pexels API (Legacy)": "pexels"
    }
    selected_visual_source = visual_source_map[visual_source_label]

    st.markdown("---")
    st.markdown("### 📐 Video Format & Duration")
    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        ["16:9 (Landscape - YouTube Long-form)", "9:16 (Portrait - Shorts/TikTok)"],
        index=0
    )
    is_vertical = ("9:16" in aspect_ratio)

    target_duration_format = st.selectbox(
        "Target Duration Preset",
        [
            "Long-form (3-5 mins) • 16-24 scenes (~550-750 words)",
            "Medium (2-3 mins) • 10-14 scenes (~350-450 words)",
            "Shorts (60s) • 4-6 scenes (~120-150 words)"
        ],
        index=0 if not is_vertical else 2
    )

    custom_scenes_toggle = st.checkbox("⚙️ Advanced: Custom Scene Count", value=False)
    if custom_scenes_toggle:
        num_scenes = st.slider("Total Scenes", min_value=5, max_value=30, value=18)
    else:
        if "Long-form" in target_duration_format:
            num_scenes = 18
        elif "Medium" in target_duration_format:
            num_scenes = 12
        else:
            num_scenes = 5

    target_calc_scenes, target_calc_words, target_calc_secs = calculate_target_metrics(target_duration_format, num_scenes)
    st.caption(f"🎯 Target: **{num_scenes} scenes** | Narration words: **~{target_calc_words} words** | Duration: **~{target_calc_secs}s ({target_calc_secs//60}m {target_calc_secs%60}s)**")

    st.markdown("---")
    st.markdown("### 🎙️ Voiceover Engine (Edge-TTS)")
    voice_label = st.selectbox("Narrator Voice", list(VOICE_PRESETS.keys()), index=0)
    selected_voice = VOICE_PRESETS[voice_label]

    speech_rate = st.slider("Speech Rate", min_value=-20, max_value=20, value=0, step=5, format="%+d%%")
    rate_str = f"{speech_rate:+d}%"

    if st.button("🎧 Preview Voice", use_container_width=True):
        preview_audio_file = os.path.join("output", "preview_voice.mp3")
        with st.spinner("Synthesizing voice sample..."):
            generate_voiceover_sync(
                "Welcome to Cosmic Mysteries. Where the laws of physics bend and the unknown begins.",
                preview_audio_file,
                voice=selected_voice,
                rate=rate_str
            )
            st.audio(preview_audio_file, format="audio/mp3")

    st.markdown("---")
    st.markdown("### 🎵 Cosmic Ambient Music")
    bgm_option = st.selectbox(
        "Background Music",
        ["Deep Space Drone (Serene Chords)", "Celestial Nebula (Atmospheric)", "None (Narration Only)"],
        index=0
    )
    bgm_volume = st.slider("Music Ducking Volume", min_value=-35, max_value=-12, value=-22, step=1, format="%d dB")

    bgm_file_map = {
        "Deep Space Drone (Serene Chords)": "assets/bgm/deep_space_drone.mp3",
        "Celestial Nebula (Atmospheric)": "assets/bgm/celestial_nebula.mp3",
        "None (Narration Only)": None
    }
    selected_bgm_path = bgm_file_map.get(bgm_option)

    st.markdown("---")
    st.markdown("### 💬 Subtitles Style")
    subtitle_style = st.selectbox(
        "Subtitle Colorway",
        ["Bold Cyber Yellow", "Glowing Cosmic Cyan", "Classic Modern White"],
        index=0
    )
    subtitle_theme_map = {
        "Bold Cyber Yellow": "cyber_yellow",
        "Glowing Cosmic Cyan": "cosmic_cyan",
        "Classic Modern White": "classic_white"
    }
    selected_sub_theme = subtitle_theme_map[subtitle_style]

    subtitle_mode = st.selectbox(
        "Caption Chunking",
        ["Punchy 3-4 Words (High Retention)", "Full Sentences (Documentary)"],
        index=0 if is_vertical else 1
    )


# --- MAIN HEADER ---
st.markdown("""
<div class="cosmic-header">
    <div class="cosmic-title">🌌 Cosmic Video Maker • Long-Form AI Studio</div>
    <div class="cosmic-subtitle">Automated YouTube Studio for 3-5 Minute Documentaries & Shorts • Full Scene-by-Scene Audio/Visual Sync • No Render Cutoffs</div>
</div>
""", unsafe_allow_html=True)


# --- TABS WORKFLOW ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. 📜 Script & Scenes",
    "2. 🎙️ Voiceover & Audio",
    "3. 🖼️ Visuals Studio",
    "4. 🎬 Video Assembly",
    "5. 📺 Player & Export"
])


# ==========================================
# TAB 1: SCRIPT & SCENE GENERATOR
# ==========================================
with tab1:
    st.subheader("Step 1: Generate & Customize Script Breakdown")
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        preset_choice = st.selectbox(
            "Or choose a popular Cosmic Mystery preset:",
            ["Custom Topic (Type Below)"] + [k.title() for k in OFFLINE_PRESETS.keys()]
        )
        
        default_topic = "What if the Moon vanished tomorrow?" if preset_choice == "Custom Topic (Type Below)" else preset_choice
        topic_input = st.text_input("Video Topic / Prompt", value=default_topic)

    with col_t2:
        provider_choice = st.selectbox(
            "AI Provider",
            ["Auto / Offline Curated", "Google Gemini", "OpenAI GPT-4o-mini"]
        )

    if st.button("✨ Generate Cosmic Script", type="primary", use_container_width=True):
        progress_script = st.progress(0.1)
        status_script = st.empty()
        status_script.text(f"Generating {num_scenes} scenes (~{target_calc_words} words) using {provider_choice}...")

        script_result = generate_script(
            topic=topic_input,
            provider=provider_choice,
            gemini_key=gemini_api_key,
            openai_key=openai_api_key,
            target_format=target_duration_format,
            num_scenes=num_scenes
        )
        
        progress_script.progress(1.0)
        status_script.text(f"Successfully generated {len(script_result.scenes)} scenes!")
        st.session_state.script = script_result
        st.session_state.scene_clips = {}
        st.session_state.scene_images = {}
        st.session_state.audio_manifest = None
        st.session_state.audio_path = None
        st.success(f"Generated script: '{script_result.title}' with {len(script_result.scenes)} scenes ({len(script_result.full_narration.split())} words)!")

    # Display / Edit Script
    if st.session_state.script:
        scr = st.session_state.script
        st.markdown("---")
        
        col_meta1, col_meta2 = st.columns([2, 1])
        with col_meta1:
            scr.title = st.text_input("Title", value=scr.title)
            scr.hook = st.text_input("Hook (First 5 Seconds)", value=scr.hook)
            scr.description = st.text_area("YouTube Description", value=scr.description, height=75)
        with col_meta2:
            st.markdown(f"**Target Format:** {scr.target_format}")
            st.markdown(f"**Total Scenes:** `{len(scr.scenes)}` | **Narration Words:** `{len(scr.full_narration.split())}`")
            tag_str = ", ".join(scr.tags)
            scr.tags = [t.strip() for t in st.text_input("SEO Tags", value=tag_str).split(",") if t.strip()]

        st.markdown("### 📊 Interactive Scene Editor Table")
        st.caption("You can review and edit narration sentences or stock keywords directly in the table below:")

        # Build DataFrame for interactive table editor
        table_data = []
        for s in scr.scenes:
            table_data.append({
                "Scene #": s.scene_id,
                "Heading": s.heading,
                "Narration (Spoken Text)": s.narration,
                "Stock Keyword (Pixabay/Local)": s.visual_keyword,
                "Words": len(s.narration.split())
            })
        df_scenes = pd.DataFrame(table_data)
        
        edited_df = st.data_editor(
            df_scenes,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Scene #": st.column_config.NumberColumn(disabled=True, width="small"),
                "Heading": st.column_config.TextColumn(width="medium"),
                "Narration (Spoken Text)": st.column_config.TextColumn(width="large"),
                "Stock Keyword (Pixabay/Local)": st.column_config.TextColumn(width="medium"),
                "Words": st.column_config.NumberColumn(disabled=True, width="small"),
            }
        )

        # Sync table edits back to session state
        if st.button("💾 Apply Table Edits to Script"):
            for idx, row in edited_df.iterrows():
                if idx < len(scr.scenes):
                    scr.scenes[idx].heading = str(row["Heading"])
                    scr.scenes[idx].narration = str(row["Narration (Spoken Text)"])
                    scr.scenes[idx].visual_keyword = str(row["Stock Keyword (Pixabay/Local)"])
                    scr.scenes[idx].stock_query = scr.scenes[idx].visual_keyword
            scr.full_narration = " ".join([s.narration for s in scr.scenes])
            st.success("Applied all edits to scenes!")

        with st.expander(f"🔍 Detailed Scene Prompt Cards ({len(scr.scenes)} scenes)", expanded=False):
            for idx, scene in enumerate(scr.scenes):
                with st.container():
                    st.markdown(f"""
                    <div class="scene-card">
                        <span class="scene-badge">Scene #{scene.scene_id} &bull; ~{len(scene.narration.split())} words</span>
                    </div>
                    """, unsafe_allow_html=True)
                    col_s1, col_s2 = st.columns([3, 2])
                    with col_s1:
                        scene.heading = st.text_input(f"Heading #{scene.scene_id}", value=scene.heading, key=f"head_{idx}")
                        scene.narration = st.text_area(f"Narration #{scene.scene_id}", value=scene.narration, height=80, key=f"narr_{idx}")
                    with col_s2:
                        scene.visual_keyword = st.text_input(f"Stock Keyword #{scene.scene_id}", value=scene.visual_keyword, key=f"pex_{idx}")
                        scene.visual_prompt = st.text_area(f"AI Visual Prompt #{scene.scene_id}", value=scene.visual_prompt, height=80, key=f"prompt_{idx}")


# ==========================================
# TAB 2: VOICEOVER & SUBTITLES
# ==========================================
with tab2:
    st.subheader("Step 2: Scene-by-Scene Audio Synthesis & Subtitles")
    
    if not st.session_state.script:
        st.warning("Please generate a script in Step 1 first.")
    else:
        scr = st.session_state.script
        st.write(f"**Narration Script:** `{len(scr.scenes)}` scenes | Total words: `{len(scr.full_narration.split())}`")

        if st.button("🎙️ Generate Voiceover & Subtitles (Scene-by-Scene)", type="primary", use_container_width=True):
            audio_progress = st.progress(0.0)
            audio_status = st.empty()

            def audio_cb(pct: float, msg: str):
                audio_progress.progress(pct)
                audio_status.text(msg)

            manifest = generate_all_scenes_audio(
                scenes=scr.scenes,
                output_dir="output",
                voice=selected_voice,
                rate=rate_str,
                bgm_path=selected_bgm_path,
                bgm_volume_db=float(bgm_volume),
                aspect_ratio=aspect_ratio,
                style_theme=selected_sub_theme,
                mode="shorts_punchy" if "Punchy" in subtitle_mode else "sentence",
                progress_callback=audio_cb
            )

            st.session_state.audio_manifest = manifest
            st.session_state.audio_path = manifest["master_mixed_audio_path"]
            st.session_state.subtitles_path = manifest["master_ass_path"]
            st.session_state.subtitle_cues = manifest["global_cues"]
            st.session_state.total_duration = manifest["total_duration"]

            audio_status.text(f"Voiceover synthesized! Total exact duration: {manifest['total_duration']:.2f} seconds.")
            st.success(f"All {len(scr.scenes)} scene audios synthesized! Total duration: {manifest['total_duration']:.2f}s ({int(manifest['total_duration']//60)}m {int(manifest['total_duration']%60)}s).")

        if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
            st.markdown("---")
            col_a1, col_a2 = st.columns([1, 1])
            with col_a1:
                st.markdown("#### 🎧 Master Audio Player (Voiceover + Ducked BGM)")
                dur = st.session_state.total_duration
                st.metric(label="Exact Total Audio Duration", value=f"{dur:.2f}s ({int(dur//60)}m {int(dur%60)}s)")
                st.audio(st.session_state.audio_path, format="audio/mp3")

                # Show scene durations breakdown
                dur_rows = [{"Scene #": s.scene_id, "Exact Audio Duration (s)": s.audio_duration, "Narration Words": len(s.narration.split())} for s in scr.scenes]
                st.dataframe(pd.DataFrame(dur_rows), height=200, use_container_width=True)

            with col_a2:
                st.markdown("#### 💬 Synchronized Subtitles Preview")
                cues = st.session_state.subtitle_cues
                if cues:
                    with st.expander(f"View {len(cues)} Subtitle Segments", expanded=True):
                        for c in cues[:15]:
                            st.write(f"⏱️ `{c.start:05.2f}s` ➔ `{c.end:05.2f}s`: **{c.text}**")
                        if len(cues) > 15:
                            st.caption(f"... and {len(cues) - 15} more cues across the full video.")


# ==========================================
# TAB 3: VISUAL ASSETS STUDIO
# ==========================================
with tab3:
    st.subheader("Step 3: Fetch & Customize Scene Visuals")

    if not st.session_state.script:
        st.warning("Please generate a script in Step 1 first.")
    else:
        scr = st.session_state.script
        
        col_v_act1, col_v_act2 = st.columns([2, 1])
        with col_v_act1:
            local_cnt = len(list_local_videos())
            st.info(f"**Visual Engine Mode:** `{visual_source_label}` &bull; Local library has **{local_cnt}** offline clips in `assets/videos/`. Visual clips will be forced to match each scene's exact audio duration.")
        with col_v_act2:
            fetch_all_btn = st.button("🚀 Auto-Fetch All Visuals", type="primary", use_container_width=True)

        if fetch_all_btn:
            vis_progress = st.progress(0.0)
            vis_status = st.empty()
            
            total_scenes = len(scr.scenes)
            for idx, scene in enumerate(scr.scenes):
                pct = (idx + 1) / total_scenes
                # Crucial Fix: Use exact scene audio duration if available, else duration_est
                target_scene_dur = scene.audio_duration if scene.audio_duration > 0 else scene.duration_est
                vis_status.text(f"Preparing Scene #{scene.scene_id}/{total_scenes}: '{scene.visual_keyword}' (duration: {target_scene_dur:.2f}s)...")
                
                vid_path = os.path.join("output", f"scene_{scene.scene_id}.mp4")
                img_path = os.path.join("output", f"scene_{scene.scene_id}.png")
                
                out_clip = fetch_or_generate_scene_visual(
                    scene_id=scene.scene_id,
                    query=scene.visual_keyword,
                    pixabay_key=pixabay_api_key,
                    pexels_key=pexels_api_key,
                    aspect_ratio=aspect_ratio,
                    target_duration=target_scene_dur,
                    output_video_path=vid_path,
                    output_image_path=img_path,
                    preferred_source=selected_visual_source
                )
                
                scene.video_clip_path = out_clip
                st.session_state.scene_clips[scene.scene_id] = out_clip
                st.session_state.scene_images[scene.scene_id] = img_path
                vis_progress.progress(pct)

            vis_status.text("All scene visuals prepared successfully!")
            st.success(f"All {total_scenes} scene visuals ready and strictly bound to narration durations!")

        st.markdown("---")
        st.markdown("### 🖼️ Scene Assets Grid")

        cols = st.columns(min(3, len(scr.scenes)))
        for idx, scene in enumerate(scr.scenes):
            col_target = cols[idx % len(cols)]
            with col_target:
                dur_tag = f"{scene.audio_duration:.1f}s" if scene.audio_duration > 0 else f"{scene.duration_est:.1f}s"
                st.markdown(f"**Scene {scene.scene_id}: {scene.heading}** (`{dur_tag}`)")
                
                current_clip = st.session_state.scene_clips.get(scene.scene_id)
                current_img = st.session_state.scene_images.get(scene.scene_id)
                
                if current_img and os.path.exists(current_img):
                    st.image(current_img, use_container_width=True, caption=f"Stock Query: {scene.visual_keyword}")
                elif current_clip and os.path.exists(current_clip):
                    st.video(current_clip)
                else:
                    st.caption("No asset loaded yet. Click 'Auto-Fetch All Visuals' or select below.")

                # Option A: Pick directly from local assets/videos/
                local_files = list_local_videos()
                if local_files:
                    local_names = [os.path.basename(f) for f in local_files]
                    chosen_local = st.selectbox(
                        f"Pick from Local Assets:",
                        ["(Auto-matched)"] + local_names,
                        key=f"local_pick_{scene.scene_id}"
                    )
                    if chosen_local != "(Auto-matched)":
                        local_full = os.path.join("assets", "videos", chosen_local)
                        if st.button(f"Use {chosen_local}", key=f"apply_loc_{scene.scene_id}"):
                            vid_path = os.path.join("output", f"scene_{scene.scene_id}.mp4")
                            img_path = os.path.join("output", f"scene_{scene.scene_id}.png")
                            target_dur = scene.audio_duration if scene.audio_duration > 0 else scene.duration_est
                            processed = fetch_or_generate_scene_visual(
                                scene_id=scene.scene_id,
                                query=scene.visual_keyword,
                                aspect_ratio=aspect_ratio,
                                target_duration=target_dur,
                                output_video_path=vid_path,
                                output_image_path=img_path,
                                custom_asset_path=local_full
                            )
                            st.session_state.scene_clips[scene.scene_id] = processed
                            st.rerun()

                # Option B: Upload custom AI image/video
                uploaded_file = st.file_uploader(
                    f"Or Upload Custom Asset (Scene {scene.scene_id})",
                    type=["png", "jpg", "jpeg", "mp4", "mov"],
                    key=f"uploader_{scene.scene_id}"
                )
                if uploaded_file is not None:
                    custom_save_path = os.path.join("output", f"custom_scene_{scene.scene_id}_{uploaded_file.name}")
                    with open(custom_save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    vid_path = os.path.join("output", f"scene_{scene.scene_id}.mp4")
                    img_path = os.path.join("output", f"scene_{scene.scene_id}.png")
                    target_dur = scene.audio_duration if scene.audio_duration > 0 else scene.duration_est
                    
                    processed = fetch_or_generate_scene_visual(
                        scene_id=scene.scene_id,
                        query=scene.visual_keyword,
                        aspect_ratio=aspect_ratio,
                        target_duration=target_dur,
                        output_video_path=vid_path,
                        output_image_path=img_path,
                        custom_asset_path=custom_save_path
                    )
                    st.session_state.scene_clips[scene.scene_id] = processed
                    st.success(f"Applied custom asset for Scene {scene.scene_id}!")


# ==========================================
# TAB 4: VIDEO ASSEMBLY & RENDERING
# ==========================================
with tab4:
    st.subheader("Step 4: Assemble & Render Final Video")

    ready_to_render = True
    if not st.session_state.script:
        st.warning("⚠️ Script is missing. Please complete Step 1.")
        ready_to_render = False
    elif not st.session_state.audio_path:
        st.warning("⚠️ Voiceover audio is missing. Please complete Step 2.")
        ready_to_render = False
    elif not st.session_state.scene_clips or len(st.session_state.scene_clips) < len(st.session_state.script.scenes):
        st.warning(f"⚠️ Some scene visuals are missing ({len(st.session_state.scene_clips)}/{len(st.session_state.script.scenes)} prepared). Please complete Step 3.")
        ready_to_render = False

    if ready_to_render:
        scr = st.session_state.script
        total_audio_dur = st.session_state.total_duration
        
        # Summary metrics
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Total Scenes", f"{len(scr.scenes)}")
        with col_m2:
            st.metric("Target Duration", f"{total_audio_dur:.1f}s ({int(total_audio_dur//60)}m {int(total_audio_dur%60)}s)")
        with col_m3:
            st.metric("Aspect Ratio", f"{'9:16 Shorts' if is_vertical else '16:9 Landscape'}")
        with col_m4:
            st.metric("Subtitles", f"{subtitle_style}")

        st.markdown("---")
        
        if st.button("🚀 Render Final Cosmic Video (Full Duration)", type="primary", use_container_width=True):
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            
            def render_callback(pct: float, msg: str):
                progress_bar.progress(pct)
                status_text.text(msg)

            output_filename = f"cosmic_{scr.title[:20].lower().replace(' ', '_').replace('?', '')}_{int(time.time())}.mp4"
            final_mp4_path = os.path.join("output", output_filename)

            # Sort clips strictly by scene_id
            sorted_clips = [st.session_state.scene_clips[s.scene_id] for s in scr.scenes]

            try:
                rendered_path = render_final_video(
                    scene_clips=sorted_clips,
                    audio_path=st.session_state.audio_path,
                    output_video_path=final_mp4_path,
                    subtitles_path=st.session_state.subtitles_path,
                    aspect_ratio=aspect_ratio,
                    target_total_duration=total_audio_dur,
                    video_bitrate="4000k",
                    progress_callback=render_callback
                )
                
                info = get_video_info(rendered_path)
                st.session_state.final_video_path = rendered_path
                st.session_state.video_info = info
                st.balloons()
                st.success(f"Video successfully rendered to `{rendered_path}`! Duration: {info.get('duration', 0):.1f}s.")
                st.info("Switch to Tab 5 (Player & Export) to preview and download your video.")

            except Exception as e:
                st.error(f"Render Error: {e}")


# ==========================================
# TAB 5: VIDEO PLAYER & EXPORT
# ==========================================
with tab5:
    st.subheader("Step 5: Preview & Download Rendered Video")

    if not st.session_state.final_video_path or not os.path.exists(st.session_state.final_video_path):
        st.info("No rendered video found yet. Complete Step 4 to render your masterpiece!")
    else:
        final_path = st.session_state.final_video_path
        info = st.session_state.video_info
        scr = st.session_state.script

        col_p1, col_p2 = st.columns([3, 2])
        
        with col_p1:
            st.markdown("### 🎥 Broadcast Preview")
            st.video(final_path)
            
            with open(final_path, "rb") as f:
                video_bytes = f.read()

            st.download_button(
                label="⬇️ Download Final MP4 Video",
                data=video_bytes,
                file_name=os.path.basename(final_path),
                mime="video/mp4",
                type="primary",
                use_container_width=True
            )

        with col_p2:
            st.markdown("### 📊 Video Metadata")
            st.markdown(f"""
            - **Resolution:** `{info.get('width', 1920)} x {info.get('height', 1080)}`
            - **Duration:** `{info.get('duration', 0):.2f}` seconds ({int(info.get('duration', 0)//60)}m {int(info.get('duration', 0)%60)}s)
            - **Frame Rate:** `{info.get('fps', 30)}` FPS
            - **File Size:** `{info.get('size_mb', 0)}` MB
            - **Video Bitrate:** `4000 kbps (High Quality H.264)`
            - **Audio Codec:** `AAC 192 kbps (Voiceover + Ducked Ambient BGM)`
            """)

            if scr:
                st.markdown("### 📋 YouTube Publishing Kit")
                st.text_input("Title (Ready to copy)", value=scr.title)
                st.text_area("Description (Ready to copy)", value=f"{scr.description}\n\n#space #cosmicmysteries #science #{'shorts' if is_vertical else 'documentary'}", height=120)
                st.text_input("Tags", value=", ".join(scr.tags))

st.markdown("---")
st.caption("Cosmic Video Maker &copy; 2026 - Powered by Streamlit, FFmpeg, Edge-TTS, and Google Gemini.")
