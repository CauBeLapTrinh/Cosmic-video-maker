"""
Module 1: Script & Prompt Generator
Refactored to support long-form videos (3 to 5 minutes) with 15-25 scenes,
dynamic word/scene calculation, strict JSON schema validation, and retry logic.
"""

import os
import json
import re
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Scene:
    scene_id: int
    heading: str
    narration: str
    visual_prompt: str
    visual_keyword: str
    duration_est: float = 12.0  # in seconds
    pexels_query: str = ""      # alias for backward compatibility
    stock_query: str = ""       # alias
    audio_duration: float = 0.0 # exact measured duration after TTS synthesis
    audio_path: str = ""
    video_clip_path: str = ""

    def __post_init__(self):
        # Synchronize keyword aliases
        if not self.visual_keyword:
            self.visual_keyword = self.stock_query or self.pexels_query or "space galaxy"
        if not self.stock_query:
            self.stock_query = self.visual_keyword
        if not self.pexels_query:
            self.pexels_query = self.visual_keyword
        if not self.heading:
            self.heading = f"Scene {self.scene_id}"


@dataclass
class CosmicScript:
    title: str
    hook: str
    topic: str
    target_format: str  # "Shorts (60s)", "Medium (2-3 min)", "Long-form (3-5 min)"
    total_estimated_duration: float
    scenes: List[Scene]
    full_narration: str
    tags: List[str]
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "hook": self.hook,
            "topic": self.topic,
            "target_format": self.target_format,
            "total_estimated_duration": self.total_estimated_duration,
            "scenes": [asdict(s) for s in self.scenes],
            "full_narration": self.full_narration,
            "tags": self.tags,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CosmicScript":
        scenes = [Scene(**s) for s in data.get("scenes", [])]
        return cls(
            title=data.get("title", "Cosmic Mystery"),
            hook=data.get("hook", ""),
            topic=data.get("topic", "Cosmic Mystery"),
            target_format=data.get("target_format", "Long-form (3-5 min)"),
            total_estimated_duration=data.get("total_estimated_duration", 240.0),
            scenes=scenes,
            full_narration=data.get("full_narration", ""),
            tags=data.get("tags", []),
            description=data.get("description", "")
        )


def calculate_target_metrics(target_format: str, custom_scenes: Optional[int] = None) -> Tuple[int, int, int]:
    """
    Calculates (num_scenes, total_target_words, target_duration_seconds) based on target format.
    Average English speech rate: ~140-150 words per minute.
    - Shorts (60s): 5 scenes, ~130 words, ~60s
    - Medium (2-3 min): 12 scenes, ~380 words, ~160s
    - Long-form (3-5 min): 18 scenes, ~650 words, ~240s
    """
    if custom_scenes and custom_scenes >= 4:
        num_scenes = custom_scenes
        total_words = int(num_scenes * 32)
        total_seconds = int(num_scenes * 12.5)
        return num_scenes, total_words, total_seconds

    fmt = target_format.lower()
    if "short" in fmt or "60s" in fmt:
        return 5, 130, 60
    elif "medium" in fmt or "2-3" in fmt:
        return 12, 380, 160
    else:  # Long-form (3-5 min) default
        return 18, 650, 240


# Expanded curated scenes for offline generator (supports up to 24 scenes)
LONG_FORM_OFFLINE_TEMPLATES = [
    ("The Sudden Disappearance", "Tonight, look up into the night sky. Now imagine the Moon has simply vanished into thin air. At first, darkness consumes the night, but the true planetary nightmare is only beginning.", "dark moon starry sky night horizon", "Cinematic 8k shot of a starry night sky where the full moon abruptly dissolves into glowing gravitational dust"),
    ("Collapse of the Tides", "Within mere hours, the pulse of our oceans collapses. Without lunar gravitational pull, global ocean tides shrink by over sixty percent, stalling coastal currents and stranding marine life.", "ocean storm waves dark tide", "Violent dramatic ocean tidal shift, receding waters exposing dark sea floor beneath a moonless starry sky"),
    ("Planetary Axis Wobble", "For billions of years, the Moon acted as Earth's gravitational gyroscope. Without it, our planet's axial tilt begins to wobble wildly, destabilizing the climate over centuries.", "planet earth space wobble axis", "Earth spinning erratically in deep space without its moon, chaotic weather storm vortices across continents"),
    ("Chaos of the Seasons", "As the tilt shifts between zero and eighty-five degrees, the seasons descend into madness. Tropical zones freeze under sudden glacial sheets, while polar ice caps boil away in blistering heat.", "glacier melting ice storm lightning", "Polar glaciers collapsing under extreme lightning storms, dramatic climate catastrophe landscape"),
    ("Tectonic Unrest", "The sudden redistribution of millions of tons of ocean water releases tremendous pressure on continental plates. Subterranean faults slip, triggering violent earthquakes along coastal rims.", "volcano eruption lava earth fissure", "Cracked tectonic plates with glowing orange magma fractures across coastal mountain ranges, epic scale"),
    ("Loss of the Cosmic Bodyguard", "For four billion years, the Moon absorbed thousands of cataclysmic asteroid impacts. Without our loyal celestial shield, Earth stands utterly exposed to the wandering debris of deep space.", "asteroid meteor cluster space earth", "Cluster of fiery asteroids hurtling toward Earth through deep cosmos, glowing orange heat shield impact trails"),
    ("Night Sky Transformation", "Our nights become profoundly, eerily dark. Without lunar reflection, the Milky Way blazes with blinding clarity, but nocturnal predators and ecosystems face immediate sensory collapse.", "milky way galaxy dark night sky", "Milky way galaxy arching across a pitch black sky over dark silhouette mountains, ultra-detailed 8k"),
    ("Atmospheric Disruptions", "Tidal bulges also existed in Earth's atmosphere. With lunar forces removed, high-altitude jet streams warp, spawning perpetual superstorms that race across oceans at hundreds of miles per hour.", "supercell storm tornado lightning space", "Massive hurricane vortex seen from low Earth orbit, lightning dancing across cloud tops"),
    ("The Magnetic Shield Dilemma", "Earth's liquid iron core relies subtly on tidal torque to maintain its dynamo. Over millennia, the weakening geomagnetic shield allows solar wind radiation to erode our precious upper atmosphere.", "aurora borealis solar wind earth shield", "Solar wind ribbons crashing into Earth's glowing green and violet magnetosphere in outer space"),
    ("Marine Food Chain Collapse", "Intertidal zones—the nursery of the global ocean—dry up permanently. Micro-organisms and krill populations crash, triggering a catastrophic domino effect throughout the marine food web.", "coral reef underwater dark sea", "Empty desolate underwater seabed with dim rays of sunlight filtering through dark waters"),
    ("Ancient Rhythms Broken", "Biological clocks evolved over millions of years around lunar phases. From coral spawning to bird migrations, the natural cadence of Earth's biosphere is irrevocably fractured.", "flock birds flying dark sunset", "Silhouette of birds migrating across a surreal crimson and dark violet twilight sky"),
    ("Accelerated Planetary Spin", "Without the Moon's tidal friction slowing Earth down, our days would remain rigidly locked, yet over deep time, planetary spin could fluctuate unpredictably, altering atmospheric pressure.", "fast rotating earth clouds satellite", "High-speed timelapse of Earth clouds swirling violently across blue oceans"),
    ("The Search for Solutions", "In this altered world, humanity would look to the stars with newfound urgency. Could advanced gravitational engineering or artificial planetary stabilizers ever replace our lost companion?", "futuristic space station orbit earth", "Gigantic orbital ring station constructed around Earth, glowing with blue ion engines"),
    ("The James Webb Perspective", "Telescopes peering at exoplanetary systems now confirm what we took for granted: rocky planets without large stabilizing moons rarely maintain temperate life-supporting atmospheres.", "space telescope deep cosmos star cluster", "Space telescope floating near glowing spiral galaxy, hexagonal gold mirrors reflecting starlight"),
    ("The Fragility of Habitability", "Life on Earth did not flourish by accident. It is the exquisite result of a delicate cosmic partnership forged in a giant collision four point five billion years ago.", "proto earth theia planet collision", "Giant collision between proto-Earth and planet Theia, molten rock spraying into orbit to form the Moon"),
    ("A Cold Interstellar Future", "Every breath of wind, every predictable season, every rhythm of life on our world is bound to the celestial dance above our heads.", "deep space stars void nebula", "Vast empty cosmos with distant glowing nebulae and solitary planets drifting in peace"),
    ("The Final Reckoning", "The Moon was never just an ornament in the dark. It was the silent guardian that allowed our civilization to exist.", "full moon earth golden horizon", "Glorious cinematic shot of Earth and the glowing Moon side by side in deep starry space"),
    ("The Call to the Unknown", "What other cosmic pillars hold our reality together? Subscribe to Cosmic Mysteries as we continue exploring the edge of the known universe.", "galaxy spiral universe cosmic web", "Mesmerizing infinite web of galaxies stretching into the deep purple universe, 8k cinematic masterpiece")
]


def _extract_json_from_text(raw_text: str) -> Optional[Dict[str, Any]]:
    """Extracts JSON object from text or markdown fences."""
    try:
        return json.loads(raw_text.strip())
    except Exception:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = raw_text[start:end+1]
        try:
            return json.loads(snippet)
        except Exception:
            pass

    return None


def generate_offline_script(
    topic: str,
    target_format: str = "Long-form (3-5 min)",
    custom_scenes: Optional[int] = None
) -> CosmicScript:
    """
    Generates a high-retention, documentary script matching target scene count and duration.
    """
    num_scenes, target_words, target_dur = calculate_target_metrics(target_format, custom_scenes)
    
    title = f"Cosmic Mystery: {topic.title()}"
    hook = f"Tonight, look up into the deep void of space. What if the fundamental rules governing {topic} suddenly shattered?"

    # Build scenes by drawing from rich templates or algorithmic expansion
    scenes: List[Scene] = []
    for i in range(num_scenes):
        tmpl_idx = i % len(LONG_FORM_OFFLINE_TEMPLATES)
        heading_base, narr_base, keyword_base, prompt_base = LONG_FORM_OFFLINE_TEMPLATES[tmpl_idx]
        
        # Customize narration with topic if beyond default template count
        if i >= len(LONG_FORM_OFFLINE_TEMPLATES):
            heading = f"Phase {i+1}: The {topic.title()} Phenomenon"
            narration = f"As the cosmic timeline progresses in scene {i+1}, the gravitational and physical repercussions of {topic} expand across the solar system, testing the limits of known astrophysical models."
            keyword = f"{topic} space cosmos stars"
            prompt = f"Cinematic 8k photorealistic space view of {topic} with cosmic shockwaves, deep nebula lighting"
        else:
            heading = f"Scene {i+1}: {heading_base}"
            narration = narr_base
            keyword = keyword_base
            prompt = prompt_base

        scenes.append(Scene(
            scene_id=i + 1,
            heading=heading,
            narration=narration,
            visual_prompt=prompt,
            visual_keyword=keyword,
            duration_est=round(target_dur / num_scenes, 1)
        ))

    full_narration = " ".join([s.narration for s in scenes])
    
    return CosmicScript(
        title=title,
        hook=hook,
        topic=topic,
        target_format=target_format,
        total_estimated_duration=float(target_dur),
        scenes=scenes,
        full_narration=full_narration,
        tags=["space", "cosmic mysteries", "universe", "astronomy", "what if", "astrophysics"],
        description=f"An in-depth documentary exploring the cosmic mystery: {topic}. Complete scene-by-scene scientific breakdown."
    )


def _build_system_prompt(topic: str, target_format: str, num_scenes: int, target_words: int) -> str:
    words_per_scene = max(25, int(target_words / num_scenes))
    return f"""You are a master scientific documentarian and YouTube script director specializing in the viral YouTube niche: "Cosmic Mysteries & What-If Scenarios" (in the style of Kurzgesagt, Melodysheep, and Astrum).

Task: Write a high-retention video script breakdown for:
Topic: "{topic}"
Target Format: {target_format}
Required Scene Count: EXACTLY {num_scenes} scenes (Do NOT stop early. You MUST output all {num_scenes} scenes).
Total Narration Words Target: {target_words} words (~{words_per_scene} words per scene).

CRITICAL REQUIREMENTS:
1. Pacing & Tone: Dramatic, awe-inspiring, scientifically grounded, high-retention documentary narration.
2. Structure:
   - Scene 1 MUST be an immediate 5-second hook.
   - Middle scenes explore chronological escalation, physical mechanisms, gravitational consequences, and scientific theories.
   - Final scenes offer philosophical perspective and call to action.
3. Every single scene must have between 25 and 35 words of spoken narration.
4. "visual_keyword": 3 to 5 simple, searchable keywords for stock video search (e.g. 'black hole deep space 4k', 'earth night orbit', 'ocean waves storm night', 'supernova explosion').
5. "visual_prompt": A high-detail Midjourney/Stable Diffusion cinematic prompt describing the visual in 8k resolution.

YOU MUST RESPOND ONLY WITH RAW VALID JSON MATCHING THIS EXACT SCHEMA:
{{
  "title": "Compelling YouTube Video Title",
  "hook": "First 5-second hook sentence",
  "total_estimated_duration_seconds": {num_scenes * 12},
  "description": "Engaging 2-sentence YouTube video description",
  "tags": ["space", "astronomy", "what if", "cosmic mysteries", "universe"],
  "scenes": [
    {{
      "scene_id": 1,
      "heading": "Scene Title",
      "narration": "Full spoken sentence for this scene ({words_per_scene} words)...",
      "visual_keyword": "astronomy deep space galaxy 4k",
      "visual_prompt": "Cinematic visual description for AI generation"
    }}
  ]
}}
Do NOT omit any scene. Provide all {num_scenes} scenes from scene_id 1 to {num_scenes}. Output ONLY valid JSON."""


def generate_script_gemini(
    topic: str,
    api_key: str,
    target_format: str = "Long-form (3-5 min)",
    custom_scenes: Optional[int] = None
) -> CosmicScript:
    """
    Generates script using Google Gemini API with validation and retry logic.
    """
    if not api_key:
        raise ValueError("Google Gemini API Key is missing.")

    num_scenes, target_words, target_dur = calculate_target_metrics(target_format, custom_scenes)
    prompt = _build_system_prompt(topic, target_format, num_scenes, target_words)

    text_response = ""
    # Attempt 1: Modern google-genai SDK
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text_response = response.text or ""
    except Exception as e_mod:
        # Fallback to legacy SDK if needed
        try:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            text_response = response.text or ""
        except Exception as e_leg:
            raise RuntimeError(f"Gemini API request failed: {e_mod}; Fallback: {e_leg}")

    data = _extract_json_from_text(text_response)
    raw_scenes = data.get("scenes", []) if data else []

    # Retry logic if returned scenes count is significantly less than requested (e.g. < 70% of target)
    if len(raw_scenes) < int(num_scenes * 0.7):
        print(f"[Warning] Gemini generated {len(raw_scenes)}/{num_scenes} scenes. Executing expansion retry...")
        retry_prompt = f"""You previously returned only {len(raw_scenes)} scenes, but this is a {target_format} video requiring EXACTLY {num_scenes} scenes.
Please rewrite the full script for topic '{topic}' with EXACTLY {num_scenes} scenes (numbered 1 to {num_scenes}).
Output raw JSON only matching the schema:
{{"title": "...", "scenes": [{{"scene_id": 1, "narration": "...", "visual_keyword": "...", "visual_prompt": "..."}}]}}"""
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            resp_retry = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=retry_prompt
            )
            data_retry = _extract_json_from_text(resp_retry.text or "")
            if data_retry and len(data_retry.get("scenes", [])) > len(raw_scenes):
                data = data_retry
                raw_scenes = data.get("scenes", [])
        except Exception as e_retry:
            print(f"[Retry warning] Retry attempt did not succeed ({e_retry}), using initial output with padding.")

    # If still fewer than requested, algorithmically pad scenes to guarantee target scene count
    if len(raw_scenes) < num_scenes:
        needed = num_scenes - len(raw_scenes)
        print(f"[Info] Padding {needed} supplementary scenes to fulfill full {num_scenes} scenes requirement.")
        offline_fallback = generate_offline_script(topic, target_format, custom_scenes=num_scenes)
        for i in range(len(raw_scenes), num_scenes):
            pad_s = offline_fallback.scenes[i]
            raw_scenes.append({
                "scene_id": i + 1,
                "heading": pad_s.heading,
                "narration": pad_s.narration,
                "visual_keyword": pad_s.visual_keyword,
                "visual_prompt": pad_s.visual_prompt
            })

    scenes: List[Scene] = []
    for idx, s in enumerate(raw_scenes[:num_scenes], 1):
        keyword = s.get("visual_keyword") or s.get("pexels_query") or s.get("stock_query") or "space deep cosmos"
        prompt = s.get("visual_prompt") or f"Cinematic 8k view of {topic}"
        scenes.append(Scene(
            scene_id=idx,
            heading=s.get("heading", f"Scene {idx}"),
            narration=s.get("narration", ""),
            visual_prompt=prompt,
            visual_keyword=keyword,
            duration_est=round(target_dur / num_scenes, 1)
        ))

    full_narration = " ".join([s.narration for s in scenes])
    return CosmicScript(
        title=data.get("title", f"Cosmic Mystery: {topic}"),
        hook=data.get("hook", scenes[0].narration if scenes else ""),
        topic=topic,
        target_format=target_format,
        total_estimated_duration=float(target_dur),
        scenes=scenes,
        full_narration=full_narration,
        tags=data.get("tags", ["space", "universe", "cosmic mysteries", "astronomy"]),
        description=data.get("description", f"Documentary about {topic}")
    )


def generate_script_openai(
    topic: str,
    api_key: str,
    target_format: str = "Long-form (3-5 min)",
    custom_scenes: Optional[int] = None
) -> CosmicScript:
    """
    Generates script using OpenAI GPT-4o-mini with rigid JSON schema.
    """
    if not api_key:
        raise ValueError("OpenAI API Key is missing.")

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    num_scenes, target_words, target_dur = calculate_target_metrics(target_format, custom_scenes)
    prompt = _build_system_prompt(topic, target_format, num_scenes, target_words)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a professional science documentary scriptwriter who outputs only raw JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    raw_text = response.choices[0].message.content or ""
    data = _extract_json_from_text(raw_text)
    raw_scenes = data.get("scenes", []) if data else []

    if len(raw_scenes) < num_scenes:
        offline_fallback = generate_offline_script(topic, target_format, custom_scenes=num_scenes)
        for i in range(len(raw_scenes), num_scenes):
            pad_s = offline_fallback.scenes[i]
            raw_scenes.append({
                "scene_id": i + 1,
                "heading": pad_s.heading,
                "narration": pad_s.narration,
                "visual_keyword": pad_s.visual_keyword,
                "visual_prompt": pad_s.visual_prompt
            })

    scenes: List[Scene] = []
    for idx, s in enumerate(raw_scenes[:num_scenes], 1):
        keyword = s.get("visual_keyword") or s.get("stock_query") or s.get("pexels_query") or "space cosmos"
        prompt = s.get("visual_prompt") or f"Cinematic 8k view of {topic}"
        scenes.append(Scene(
            scene_id=idx,
            heading=s.get("heading", f"Scene {idx}"),
            narration=s.get("narration", ""),
            visual_prompt=prompt,
            visual_keyword=keyword,
            duration_est=round(target_dur / num_scenes, 1)
        ))

    full_narration = " ".join([s.narration for s in scenes])
    return CosmicScript(
        title=data.get("title", f"Cosmic Mystery: {topic}"),
        hook=data.get("hook", scenes[0].narration if scenes else ""),
        topic=topic,
        target_format=target_format,
        total_estimated_duration=float(target_dur),
        scenes=scenes,
        full_narration=full_narration,
        tags=data.get("tags", ["space", "astronomy", "science"]),
        description=data.get("description", f"Documentary on {topic}")
    )


def generate_script(
    topic: str,
    provider: str = "Auto / Offline",
    gemini_key: Optional[str] = None,
    openai_key: Optional[str] = None,
    target_format: str = "Long-form (3-5 min)",
    num_scenes: Optional[int] = None
) -> CosmicScript:
    """
    Master orchestrator function for script generation with automatic fallback.
    """
    provider = provider.lower()
    
    if "gemini" in provider and gemini_key:
        try:
            return generate_script_gemini(topic, gemini_key, target_format, custom_scenes=num_scenes)
        except Exception as e:
            print(f"[Warning] Gemini generation failed ({e}), falling back to offline generator.")
    elif "openai" in provider and openai_key:
        try:
            return generate_script_openai(topic, openai_key, target_format, custom_scenes=num_scenes)
        except Exception as e:
            print(f"[Warning] OpenAI generation failed ({e}), falling back to offline generator.")

    return generate_offline_script(topic, target_format, custom_scenes=num_scenes)
