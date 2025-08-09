import pyttsx3
import uuid
import os
import pathlib

# Directory for generated audio
AUDIO_DIR = pathlib.Path("static/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Initialize pyttsx3 engine
engine = pyttsx3.init()

def synthesize(text: str):
    """Generate speech with pyttsx3 and return local file URL"""
    if len(text) > 500:
        text = text[:500]
    filename = f"{uuid.uuid4()}.mp3"
    out_path = AUDIO_DIR / filename

    try:
        engine.save_to_file(text, str(out_path))
        engine.runAndWait()
    except Exception as e:
        print("TTS error:", e)
        return None

    return f"/static/audio/{filename}"
