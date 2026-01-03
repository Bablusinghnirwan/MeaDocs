import os
import sys
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file

# Import only lightweight modules at startup
# photo_utils is now deferred

import logging
import traceback

# Configure Logging
logging.basicConfig(
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.log"),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filemode="w"
)

# Also log to console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console.setFormatter(formatter)
logging.getLogger("").addHandler(console)

logging.info("Server starting...")

# Import modules at startup to prevent threading hangs
try:
    import photo_utils
    print("[OK] Photo utils loaded")
except Exception as e:
    logging.error(f"[ERROR] Failed to import photo_utils: {e}")
    logging.error(traceback.format_exc())
    photo_utils = None

try:
    import video_utils
    print("[OK] Video utils loaded")
except Exception as e:
    logging.error(f"[ERROR] Failed to import video_utils: {e}")
    logging.error(traceback.format_exc())
    video_utils = None

try:
    import document_utils
    print("[OK] Document utils loaded")
except Exception as e:
    logging.error(f"[ERROR] Failed to import document_utils: {e}")
    logging.error(traceback.format_exc())
    document_utils = None

try:
    import audio_utils
    # Try to use audio_utils value, but fallback if fails
    UPLOAD_FOLDER = getattr(audio_utils, "UPLOAD_FOLDER", os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads"))
    print("[OK] Audio utils loaded")
except Exception as e:
    logging.error(f"[ERROR] Failed to import audio_utils: {e}")
    logging.error(traceback.format_exc())
    audio_utils = None
    # Fallback definition if import fails
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

def _import_photo_utils():
    if photo_utils is None:
        return {"error": "Photo module failed to load at startup"}
    return photo_utils

def _import_video_utils():
    if video_utils is None:
         class DummyVideo:
            def process_videos(*args, **kwargs): raise Exception("Video module failed to load")
            def search_video(*args, **kwargs): raise Exception("Video module failed to load")
         return DummyVideo()
    return video_utils

def _import_document_utils():
    if document_utils is None:
        class DummyDoc:
            def add_document_to_store(*args, **kwargs): raise Exception("Document module failed to load")
            def search_documents(*args, **kwargs): raise Exception("Document module failed to load")
        return DummyDoc()
    return document_utils

def _import_audio_utils():
    if audio_utils is None:
        class DummyAudio:
            def process_audio_folder(*args, **kwargs): raise Exception("Audio module failed to load")
            def search_audio_files(*args, **kwargs): raise Exception("Audio module failed to load")
        return DummyAudio()
    return audio_utils

app = Flask(__name__)

# --- WINDOWS PATH CONFIGURATION ---
# Project ka main folder detect karega taaki C: drive ke errors na aayein
# Project ka main folder detect karega taaki C: drive ke errors na aayein
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure uploads folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------- Home Page ----------
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
os.environ['HF_HOME'] = CACHE_DIR
os.environ['TORCH_HOME'] = CACHE_DIR

# Ensure uploads folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------- Home Page ----------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

# ---------- Photo Search ----------
@app.route("/photo_search", methods=["GET"])
def photo_search():
    # Don't load photo_utils here - it will load when user actually searches
    # This makes page navigation instant
    return render_template("photo_search.html", indexed=False)

@app.route("/index-images", methods=["POST"])
def index_images():
    pu = _import_photo_utils()
    if isinstance(pu, dict) and "error" in pu:
        return jsonify(pu), 500
        
    data = request.get_json()
    directory = data.get("directory", "").strip()

    if not directory:
        return jsonify({"error": "Directory path missing!"}), 400
    
    # Windows Path Fix: Slash ko sahi direction mein convert karega
    directory = os.path.normpath(directory)

    if not os.path.exists(directory):
        return jsonify({"error": f"Directory not found: {directory}"}), 404

    result = pu.index_images_from_directory(directory)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)

@app.route("/search-images", methods=["POST"])
def search_images():
    pu = _import_photo_utils()
    query = request.form.get("query", "")
    results = pu.search_images_by_text(query)
    return jsonify(results)

@app.route("/serve-image")
def serve_image():
    image_path = request.args.get("path")
    
    if not image_path:
        return "Path parameter missing", 400

    # Windows Safety: Path ko normalize karo
    image_path = os.path.normpath(image_path)
    
    if not os.path.exists(image_path):
        return "Image not found", 404
        
    return send_from_directory(os.path.dirname(image_path), os.path.basename(image_path))


# ---------- Video Search ----------
@app.route("/video_search", methods=["GET"])
def video_search():
    return render_template("video_search.html")

@app.route('/process_videos', methods=['POST'])
def process_videos_route():
    vu = _import_video_utils()  # Load only when needed
    if 'directory' in request.form:
        video_directory = request.form['directory']
        # Windows Fix
        video_directory = os.path.normpath(video_directory)
        
        if not os.path.exists(video_directory):
             return jsonify({'status': 'error', 'message': 'Directory does not exist on this PC.'})

        try:
            success = vu.process_videos(video_directory)
            if success:
                return jsonify({'status': 'success', 'message': 'Video processing complete!'})
            else:
                return jsonify({'status': 'error', 'message': 'No video files found.'})
        except Exception as e:
            logging.error(f"Error processing videos: {e}")
            logging.error(traceback.format_exc())
            return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'error', 'message': 'Directory not provided.'})

@app.route('/search_video', methods=['POST'])
def search_video_route():
    vu = _import_video_utils()  # Load only when needed
    if 'query' in request.form:
        query = request.form['query']
        try:
            result = vu.search_video(query)
            if result:
                return jsonify({'status': 'success', 'result': result})
            return jsonify({'status': 'error', 'message': 'No matching video found.'})
        except Exception as e:
             logging.error(f"Error searching video: {e}")
             logging.error(traceback.format_exc())
             return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'error', 'message': 'Search query not provided.'})

@app.route("/stream-video")
def stream_video():
    video_path = request.args.get("path")
    if video_path:
        video_path = os.path.normpath(video_path)
        if os.path.exists(video_path):
            return send_file(video_path, mimetype='video/mp4')
    return "Video not found", 404

# ---------- Document Search ----------

@app.route("/document_search", methods=["GET"])
def document_search():
    return render_template("document_search.html")

@app.route("/upload_documents", methods=["POST"])
def upload_documents():
    du = _import_document_utils()  # Load only when needed
    folder = request.form.get("folder")
    
    if not folder:
        return jsonify({"error": "Folder path missing"}), 400
        
    # Windows Path Cleanup
    folder = os.path.normpath(folder)

    if not os.path.isdir(folder):
        print(f"[ERROR] Invalid folder path: {folder}")
        return jsonify({"error": "Invalid folder path"}), 400

    print(f"[START] Preprocessing documents in folder: {folder}")
    results = []

    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith((".pdf", ".docx", ".txt")):
                file_path = os.path.join(root, file)
                print(f"  -> Adding document: {file_path}")
                try:
                    du.add_document_to_store(file_path)
                    results.append(file_path)
                    print(f"    [OK] Success: {file}")
                except Exception as e:
                    logging.error(f"    [FAILED] Failed: {file} | Reason: {str(e)}")

    print(f"[DONE] Total documents processed: {len(results)}")
    return jsonify({"message": results})


@app.route("/search_documents", methods=["POST"])
def search_documents_api():
    du = _import_document_utils()  # Load only when needed
    data = request.get_json()
    query = data.get("query", "").strip()
    top_k = int(data.get("top_k", 5))

    if not query:
        return jsonify({"error": "Search query missing!"}), 400

    try:
        results = du.search_documents(query, top_k)
        return jsonify({"results": results})
    except Exception as e:
        logging.error(f"Error searching documents: {e}")
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route("/view")
def view_document():
    file = request.args.get("file")
    if not file:
        return "No file specified", 400
    
    # Windows Path Construction (Safe)
    # Assuming 'documents' folder is inside the project root
    docs_folder = os.path.join(BASE_DIR, "documents")
    file_path = os.path.join(docs_folder, file)
    
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        # Fallback check: maybe file path is absolute?
        if os.path.exists(file):
             return send_file(file)
        return f"File not found: {file_path}", 404


# ---------- Audio Search ----------
@app.route("/audio_search", methods=["GET"])
def audio_search():
    return render_template("audio_search.html")


@app.route("/upload-folder", methods=["POST"])
def upload_audio_folder():
    au = _import_audio_utils()  # Load only when needed
    if 'audio_files' not in request.files:
        return jsonify({"error": "No audio files uploaded"}), 400

    files = request.files.getlist('audio_files')

    if not files:
        return jsonify({"error": "No audio files found in request"}), 400

    print(f"[RECEIVED] {len(files)} audio files for transcription")

    # Corrected: use process_audio_folder from imported module
    try:
        results = au.process_audio_folder(files)
        print(f"[DONE] {len(results)} transcriptions done.")
        return jsonify({"status": "done"})
    except Exception as e:
        logging.error(f"Error processing audio: {e}")
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/search", methods=["GET"])
def search_audio():
    au = _import_audio_utils()  # Load only when needed
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify([])

    # Corrected: use search_audio_files
    try:
        results = au.search_audio_files(query)
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error searching audio: {e}")
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/play/<filename>")
def play_audio(filename):
    # Windows path safe join
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        return "Audio not found", 404

@app.route("/stream-audio")
def stream_audio():
    audio_path = request.args.get("path")
    if audio_path:
        audio_path = os.path.normpath(audio_path)
        if os.path.exists(audio_path):
            return send_file(audio_path, mimetype='audio/mpeg')
    return "Audio not found", 404

@app.route("/estimate-time", methods=["POST"])
def estimate_time():
    data = request.get_json()
    directory = data.get("directory", "").strip()
    file_type = data.get("type", "photo") # photo or video

    if not directory:
        return jsonify({"error": "Directory path missing!"}), 400
    
    directory = os.path.normpath(directory)
    if not os.path.exists(directory):
        return jsonify({"error": "Directory not found"}), 404

    count = 0
    extensions = ()
    
    if file_type == "photo":
        extensions = (".jpg", ".jpeg", ".png", ".bmp", ".gif")
        time_per_file = 0.5 # seconds
    elif file_type == "video":
        extensions = (".mp4", ".avi", ".mov", ".mkv")
        time_per_file = 2.0 # seconds
    else:
        return jsonify({"error": "Invalid type"}), 400

    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(extensions):
                count += 1
    
    estimated_seconds = count * time_per_file
    
    return jsonify({
        "count": count,
        "estimated_seconds": round(estimated_seconds, 1)
    })
    
if __name__ == "__main__":
    # Host 0.0.0.0 allows access from other devices on LAN
    # Disable debug and reloader for faster startup in production
    print("\n" + "="*50)
    print("MeaDocs Server Starting...")
    print("="*50 + "\n")
    print("[OK] Flask server ready!")
    print("[OK] AI models will load on-demand when needed")
    print("\n" + "="*50)
    print("Server running at: http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)