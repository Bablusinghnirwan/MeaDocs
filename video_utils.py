import os
import cv2
import torch
import numpy as np
import faiss
from PIL import Image
import clip

# Lazy loading - models will load only when needed
device = "cuda" if torch.cuda.is_available() else "cpu"
model = None
preprocess = None

def _ensure_model_loaded():
    """Load CLIP model only when needed"""
    global model, preprocess
    if model is None:
        print("Loading CLIP model for video search...")
        model, preprocess = clip.load("ViT-B/32", device=device)
        print("CLIP model loaded!")

# FAISS Index and Storage Files
FAISS_INDEX_FILE = "video_faiss.index"
EMBEDDINGS_FILE = "video_embeddings.npy"
VIDEO_MAP_FILE = "video_map.npy"
FRAME_STORE_FILE = "video_frame_store.npy"

# Initialize FAISS Index
index = faiss.IndexFlatL2(512)
video_map = {}
frame_store = {}

def load_existing_data():
    """Loads existing FAISS index and metadata if available."""
    global index, video_map, frame_store
    
    # Avoid reloading if already in memory
    if index.ntotal > 0 and video_map:
        return

    if os.path.exists(FAISS_INDEX_FILE) and os.path.exists(EMBEDDINGS_FILE):
        try:
            index = faiss.read_index(FAISS_INDEX_FILE)
            video_map = np.load(VIDEO_MAP_FILE, allow_pickle=True).item()
            frame_store = np.load(FRAME_STORE_FILE, allow_pickle=True).item()
            print("Loaded existing FAISS index and metadata.")
        except Exception as e:
             print(f"Error loading FAISS index: {e}")
             # Reset if load fails
             index = faiss.IndexFlatL2(512)
             video_map = {}
             frame_store = {}
             
    elif os.path.exists(EMBEDDINGS_FILE):
        try:
            video_map = np.load(VIDEO_MAP_FILE, allow_pickle=True).item()
            frame_store = np.load(FRAME_STORE_FILE, allow_pickle=True).item()
            embeddings = np.load(EMBEDDINGS_FILE)
            index = faiss.IndexFlatL2(512)
            index.add(embeddings)
            print("Loaded embeddings and rebuilt FAISS index.")
        except Exception as e:
            print(f"Error loading existing data: {e}")
            video_map = {}
            frame_store = {}

def save_index():
    """Saves FAISS index and metadata for fast retrieval."""
    faiss.write_index(index, FAISS_INDEX_FILE)
    np.save(VIDEO_MAP_FILE, video_map)
    np.save(FRAME_STORE_FILE, frame_store)
    if hasattr(index, 'xb'):
        np.save(EMBEDDINGS_FILE, index.xb)

def extract_frames(video_path, output_folder, frame_interval=3):
    """Extracts frames from a video at a given interval and saves them."""
    video_name = os.path.basename(video_path)
    video_frame_folder = os.path.join(output_folder, video_name)

    if os.path.exists(video_frame_folder) and os.listdir(video_frame_folder):
        print(f"Skipping frame extraction: Frames already exist for {video_name}")
        return [(os.path.join(video_frame_folder, f), float(f.split('_')[1].split('.')[0]))
                for f in os.listdir(video_frame_folder) if f.startswith('frame_')]

    os.makedirs(video_frame_folder, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    extracted_frames = []

    success, image = cap.read()
    while success:
        timestamp = frame_count / fps
        if int(timestamp) % frame_interval == 0:
            frame_filename = os.path.join(video_frame_folder, f"frame_{int(timestamp)}.jpg")
            cv2.imwrite(frame_filename, image)
            extracted_frames.append((frame_filename, timestamp))
        success, image = cap.read()
        frame_count += 1

    cap.release()
    return extracted_frames

def encode_image(image_path):
    """Converts an image into an embedding using CLIP."""
    _ensure_model_loaded()  # Load model when first needed
    image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)
    with torch.no_grad():
        image_features = model.encode_image(image)
    image_features /= image_features.norm(dim=-1, keepdim=True)
    return image_features.cpu().numpy()

def process_videos(video_folder):
    """Processes videos and updates FAISS index."""
    global index
    load_existing_data()
    video_files = [f for f in os.listdir(video_folder)
                   if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]

    if not video_files:
        print("No video files found.")
        return False

    print(f"Processing {len(video_files)} videos...")
    frame_folder = os.path.join(video_folder, "extracted_frames")
    all_embeddings = []

    for video in video_files:
        video_path = os.path.join(video_folder, video)
        frames = extract_frames(video_path, frame_folder)
        for frame, timestamp in frames:
            embedding = encode_image(frame)
            all_embeddings.append(embedding)
            video_map[len(video_map)] = (video_path, timestamp)
            frame_store[len(frame_store)] = frame

    if all_embeddings:
        index.add(np.vstack(all_embeddings))
    save_index()
    print(f"FAISS index updated with {index.ntotal} embeddings.")
    return True

def search_video(query):
    """Searches for the best matching video."""
    _ensure_model_loaded()  # Load model when first needed
    load_existing_data()
    
    query_tokenized = clip.tokenize([query]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(query_tokenized)
        text_features /= text_features.norm(dim=-1, keepdim=True)
    query_embedding = text_features.cpu().numpy()

    D, I = index.search(query_embedding, k=3)

    if I[0][0] == -1:
        return None

    best_match_index = I[0][0]
    if best_match_index in video_map:
        best_match_video, timestamp = video_map[best_match_index]
        return {"video_path": best_match_video, "timestamp": timestamp}
    return None
