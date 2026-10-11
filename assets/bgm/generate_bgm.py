"""
Generator for procedural ambient cosmic background tracks.
Generates calming, atmospheric space synth pads and drone audio.
"""
import os
import wave
import numpy as np

def generate_cosmic_drone(filename: str, duration: float = 60.0, sample_rate: int = 44100, mood: str = "deep_space"):
    """
    Generates a serene space ambient pad with warm sub-bass, harmonic drones, and slow filter sweeps.
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    if mood == "deep_space":
        # Deep space chords: D2 (73.4Hz), A2 (110Hz), D3 (146.8Hz), F#3 (185Hz)
        frequencies = [73.4, 110.0, 146.8, 185.0, 220.0]
        weights = [0.4, 0.25, 0.2, 0.12, 0.08]
    else:
        # Celestial nebula: C2 (65.4Hz), G2 (98.0Hz), D#3 (155.6Hz), G3 (196.0Hz)
        frequencies = [65.41, 98.0, 130.81, 155.56, 196.0]
        weights = [0.35, 0.28, 0.2, 0.15, 0.1]
    
    signal = np.zeros_like(t)
    for freq, weight in zip(frequencies, weights):
        # Add slight detune for lush chorus effect
        signal += weight * 0.6 * np.sin(2 * np.pi * freq * t)
        signal += weight * 0.4 * np.sin(2 * np.pi * (freq * 1.002) * t)
    
    # Very slow cosmic LFO modulation (0.08 Hz & 0.13 Hz)
    lfo1 = 0.75 + 0.25 * np.sin(2 * np.pi * 0.08 * t)
    lfo2 = 0.85 + 0.15 * np.cos(2 * np.pi * 0.05 * t + 0.5)
    signal = signal * lfo1 * lfo2
    
    # Fade in (3s) and fade out (3s)
    fade_len = int(sample_rate * 3.0)
    fade_in = np.linspace(0, 1, fade_len)
    fade_out = np.linspace(1, 0, fade_len)
    signal[:fade_len] *= fade_in
    signal[-fade_len:] *= fade_out
    
    # Normalize volume
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal = signal / max_val * 0.75
        
    audio_int16 = (signal * 32767).astype(np.int16)
    
    wav_path = filename.replace(".mp3", ".wav")
    with wave.open(wav_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    
    # Convert to MP3 if possible via ffmpeg
    mp3_path = filename if filename.endswith(".mp3") else filename + ".mp3"
    import subprocess
    cmd = [
        "ffmpeg", "-y", "-i", wav_path, 
        "-codec:a", "libmp3lame", "-b:a", "192k", 
        mp3_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(wav_path) and wav_path != mp3_path:
            os.remove(wav_path)
        return mp3_path
    except Exception:
        return wav_path

if __name__ == "__main__":
    os.makedirs("assets/bgm", exist_ok=True)
    f1 = generate_cosmic_drone("assets/bgm/deep_space_drone.mp3", duration=90.0, mood="deep_space")
    f2 = generate_cosmic_drone("assets/bgm/celestial_nebula.mp3", duration=90.0, mood="celestial")
    print(f"Generated BGM tracks: {f1}, {f2}")
