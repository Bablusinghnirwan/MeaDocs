import os
import wave
import json
import re
import sys
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment
from pydub.utils import which
from fuzzywuzzy import fuzz

# --- WINDOWS CONFIGURATION SETUP ---

# 1. Current Project Directory (Jahan ye script run ho rahi hai)
# 1. Current Project Directory (Jahan ye script run ho rahi hai)
if getattr(sys, 'frozen', False):
    # PyInstaller creates a temp folder in _MEIPASS (onefile) OR resides in directory (onedir)
    # For onedir, sys.executable is the exe path
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Folder Setup using OS-independent paths
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
TRANSCRIPTIONS_FOLDER = os.path.join(UPLOAD_FOLDER, "transcriptions")

# 3. Model Path - Relative is better than Hardcoded
# Agar model folder script ke saath pada hai to ye automatically detect karega
# 3. Model Path - Robust Detection for Packaged App
MODEL_DIR_NAME = "vosk-model-en-us-0.22-lgraph" 

# Potential paths to check
possible_paths = [
    os.path.join(BASE_DIR, MODEL_DIR_NAME), # Dev mode / Unpacked
    os.path.join(os.path.dirname(BASE_DIR), MODEL_DIR_NAME), # Parent dir
    os.path.join(os.path.dirname(sys.executable), "resources", MODEL_DIR_NAME), # Packaged resources
    os.path.join(BASE_DIR, "resources", MODEL_DIR_NAME), # Inside resources if BASE_DIR is root
    os.path.join(os.path.dirname(sys.executable), MODEL_DIR_NAME), # PyInstaller onedir
    getattr(sys, '_MEIPASS', '') and os.path.join(sys._MEIPASS, MODEL_DIR_NAME), # PyInstaller onefile
    r"D:\MeaDocs\vosk-model-en-us-0.22-lgraph" # Hardcoded Fallback
]

MODEL_PATH = None
for path in possible_paths:
    if os.path.exists(path):
        MODEL_PATH = path
        print(f"[INFO] Found Vosk model at: {MODEL_PATH}")
        break

if not MODEL_PATH:
    print(f"[ERROR] Vosk model not found! Checked: {possible_paths}")
    # Default to relative path to avoid crash, but it will fail later
    MODEL_PATH = os.path.join(BASE_DIR, MODEL_DIR_NAME)

SUPPORTED_FORMATS = (".mp3", ".wav", ".m4a", ".flac")

# --- FFMPEG CHECK FOR WINDOWS (CRITICAL) ---
# --- FFMPEG CHECK FOR WINDOWS (CRITICAL) ---
# --- FFMPEG CHECK FOR WINDOWS (CRITICAL) ---
AudioSegment.converter = which("ffmpeg")
if not AudioSegment.converter:
    # Check in project folder (dev mode) or unpacked folder (prod mode)
    # In prod, BASE_DIR is .../resources/app.asar.unpacked, so ffmpeg.exe should be there
    local_ffmpeg = os.path.join(BASE_DIR, "ffmpeg.exe")
    
    print(f"DEBUG: Checking for FFMPEG at {local_ffmpeg}")
    print(f"DEBUG: BASE_DIR is {BASE_DIR}")
    
    if os.path.exists(local_ffmpeg):
        AudioSegment.converter = local_ffmpeg
        print(f"Found FFMPEG at: {local_ffmpeg}")
    else:
        print("WARNING: FFMPEG not found! Non-WAV files (mp3) will fail.")
        print(f"Please ensure ffmpeg.exe is in {BASE_DIR}")

# Create directories
os.makedirs(TRANSCRIPTIONS_FOLDER, exist_ok=True)

# Lazy loading - model will load only when needed
model = None

def _ensure_model_loaded():
    """Load Vosk model only when needed"""
    global model
    if model is None:
        if not os.path.exists(MODEL_PATH):
            print(f"CRITICAL ERROR: Model not found at {MODEL_PATH}")
            sys.exit(1)
        print(f"Loading Vosk model from: {MODEL_PATH} ...")
        model = Model(MODEL_PATH)
        print("Vosk model loaded successfully!")

def sanitize_filename(filename):
    return re.sub(r'[^\w\-_. ]', '', filename)

def convert_to_wav(input_path, output_path):
    """Converts audio to WAV format using pydub."""
    try:
        audio = AudioSegment.from_file(input_path)
        # Vosk requires mono 16kHz
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(output_path, format="wav")
        return True
    except Exception as e:
        print(f"Error converting {input_path}: {e}")
        # Windows specific hint
        if "FileNotFound" in str(e) or "ffmpeg" in str(e).lower():
            print("HINT: Ensure FFMPEG is installed and added to Path.")
        return False

def transcribe_audio(audio_path):
    """Transcribes audio using Vosk."""
    _ensure_model_loaded()  # Load model when first needed
    
    # Convert if not WAV
    if not audio_path.endswith(".wav"):
        wav_path = os.path.splitext(audio_path)[0] + ".wav"
        success = convert_to_wav(audio_path, wav_path)
        if not success:
            return "Error: Could not convert audio file."
        audio_path = wav_path

    try:
        wf = wave.open(audio_path, "rb")
    except Exception as e:
        return f"Error opening WAV file: {e}"

    if wf.getnchannels() != 1 or wf.getframerate() != 16000:
        print(f"Audio format mismatch: {wf.getnchannels()} channels, {wf.getframerate()}Hz")
        wf.close()
        return "Error: Audio must be mono 16kHz WAV"

    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    transcript = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            transcript += result.get("text", "") + " "

    final_result = json.loads(rec.FinalResult())
    transcript += final_result.get("text", "")

    wf.close()
    return transcript.strip()

def save_transcription(filename, text):
    base_name = sanitize_filename(os.path.splitext(filename)[0])
    path = os.path.join(TRANSCRIPTIONS_FOLDER, f"{base_name}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def find_original_audio_file(base_name):
    for ext in SUPPORTED_FORMATS:
        path = os.path.join(UPLOAD_FOLDER, base_name + ext)
        if os.path.exists(path):
            return path
    return None

def process_audio_folder(files):
    results = []
    for file in files:
        filename = sanitize_filename(os.path.basename(file.filename))
        path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save file safely
        try:
            file.save(path)
        except Exception as e:
            print(f"Error saving file {filename}: {e}")
            continue

        if path.lower().endswith(SUPPORTED_FORMATS):
            transcript_path = os.path.join(TRANSCRIPTIONS_FOLDER, f"{os.path.splitext(filename)[0]}.txt")
            
            if not os.path.exists(transcript_path):
                print(f"Processing: {filename}...")
                transcript = transcribe_audio(path)
                save_transcription(filename, transcript)
                print(f"[OK] Transcribed: {filename}")
            else:
                print(f"[INFO] Already exists: {filename}")
            
            results.append(filename)
    return results

def search_audio_files(query, top_k=5):
    matches = []

    if not os.path.exists(TRANSCRIPTIONS_FOLDER):
        return []

    for text_file in os.listdir(TRANSCRIPTIONS_FOLDER):
        if text_file.endswith(".txt"):
            try:
                with open(os.path.join(TRANSCRIPTIONS_FOLDER, text_file), "r", encoding="utf-8") as f:
                    transcript = f.read()
                
                score = fuzz.partial_ratio(query.lower(), transcript.lower())
                audio_file = text_file.replace(".txt", "")
                matches.append((audio_file, score))
            except Exception as e:
                print(f"Error reading {text_file}: {e}")

    matches.sort(key=lambda x: x[1], reverse=True)
    results = []
    for file, score in matches[:top_k]:
        audio_path = find_original_audio_file(file)
        if audio_path:
            # Fix URL slashes for web response (Windows uses backslash, URLs need forward slash)
            url_path = f"/play/{os.path.basename(audio_path)}"
        else:
            url_path = None

        results.append({
            "file": file,
            "score": score,
            "url": url_path
        })

    return results