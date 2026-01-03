import os
import torch
import clip
import faiss
import numpy as np
import sys
from PIL import Image

device = "cuda" if torch.cuda.is_available() else "cpu"

# Lazy loading - models will load only when needed
model = None
preprocess = None

def _ensure_model_loaded():
    """Load CLIP model only when needed"""
    global model, preprocess
    if model is None:
        print("Loading CLIP model for photo search...")
        try:
            # Check for local model file in resources or current dir
            model_filename = "ViT-B-32.pt"
            possible_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), model_filename),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", model_filename),
                os.path.join(os.path.dirname(sys.executable), "resources", model_filename),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), model_filename) # Parent dir
            ]
            
            model_path = "ViT-B/32" # Default to download/cache
            for path in possible_paths:
                if os.path.exists(path):
                    print(f"[INFO] Found local CLIP model at: {path}")
                    model_path = path
                    break
            
            model, preprocess = clip.load(model_path, device=device, jit=False)
            print("CLIP model loaded!")
        except Exception as e:
            print(f"[ERROR] Failed to load CLIP model: {e}")
            import traceback
            traceback.print_exc()

index = None
valid_paths = []

def get_image_paths(directory):
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
    image_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            if os.path.splitext(file)[1].lower() in image_extensions:
                image_paths.append(os.path.join(root, file))
    return image_paths

def preprocess_images(image_paths):
    _ensure_model_loaded()  # Load model when first needed
    images = []
    global valid_paths
    valid_paths = []
    print(f"[INFO] Found {len(image_paths)} images to process.")
    for i, image_path in enumerate(image_paths):
        try:
            # print(f"Processing {i+1}/{len(image_paths)}: {image_path}") # Too verbose
            image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)
            images.append(image)
            valid_paths.append(image_path)
        except Exception as e:
            print(f"[ERROR] Error processing {image_path}: {e}")
    print(f"[INFO] Successfully processed {len(images)} images.")
    return images

def encode_images(images):
    with torch.no_grad():
        image_features = torch.cat([model.encode_image(img) for img in images])
        image_features /= image_features.norm(dim=-1, keepdim=True)
    return image_features.cpu().numpy()

def build_faiss_index(image_features):
    d = image_features.shape[1]
    faiss_index = faiss.IndexFlatL2(d)
    faiss_index.add(image_features)
    return faiss_index

    distances, indices = index.search(text_features, top_k)
    results = []
    for j, i in enumerate(indices[0]):
        if i != -1 and i < len(valid_paths):
             results.append({"path": valid_paths[i], "score": float(distances[0][j])})
    
    return results

def save_index():
    """Saves the FAISS index and image map to disk."""
    global index, valid_paths
    if index is not None:
        faiss.write_index(index, "photo_faiss.index")
        np.save("photo_image_map.npy", valid_paths)
        print("Index and metadata saved to disk.")

def load_existing_index():
    """Loads existing FAISS index and metadata if available."""
    global index, valid_paths
    if os.path.exists("photo_faiss.index") and os.path.exists("photo_image_map.npy"):
        try:
            index = faiss.read_index("photo_faiss.index")
            valid_paths = np.load("photo_image_map.npy", allow_pickle=True).tolist()
            print(f"Loaded existing photo FAISS index with {len(valid_paths)} images.")
            return True
        except Exception as e:
            print(f"Failed to load index: {e}")
            return False
    return False

def index_images_from_directory(directory):
    global index, valid_paths

    if not os.path.exists(directory):
        return {"error": "Invalid directory"}

    image_paths = get_image_paths(directory)
    if not image_paths:
        return {"error": "No images found in the directory."}

    images = preprocess_images(image_paths)
    if not images:
         return {"error": "No valid images could be processed."}
         
    image_features = encode_images(images)
    index = build_faiss_index(image_features)
    
    # Save the index immediately
    save_index()

    return {"message": f"Successfully indexed {len(images)} images!", "indexed": True}

def search_images_by_text(query, top_k=5):
    _ensure_model_loaded()  # Load model when first needed
    global index, valid_paths
    
    # Try to load index if it's missing
    if index is None:
        print("Index not in memory, attempting to load from disk...")
        if not load_existing_index():
            return {"error": "Index not found. Please index images first."}

    query_tokenized = clip.tokenize([query]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(query_tokenized)
        text_features /= text_features.norm(dim=-1, keepdim=True)
    text_features = text_features.cpu().numpy()

    distances, indices = index.search(text_features, top_k)
    results = []
    for j, i in enumerate(indices[0]):
        if i != -1 and i < len(valid_paths):
             results.append({"path": valid_paths[i], "score": float(distances[0][j])})
    
    return results
