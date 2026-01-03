import os
import pdfplumber
import fitz  # PyMuPDF
from docx import Document
import pytesseract
from PIL import Image
from io import BytesIO
import pandas as pd
import json

# ULTRA SIMPLE - NO AI, NO SKLEARN, NO INTERNET
# Just keyword matching with Python built-ins

# Storage
document_chunks = []  # Stores the actual text chunks
document_filenames = [] # Stores filename for each chunk
document_index_file = "document_index.json"

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
    return text


def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error reading DOCX {file_path}: {e}")
        return ""


def extract_text_from_txt(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading TXT {file_path}: {e}")
        return ""


def extract_text_from_excel(file_path):
    try:
        df = pd.read_excel(file_path, sheet_name=None)
        text = ""
        for sheet_name, sheet_data in df.items():
            text += f"\nSheet: {sheet_name}\n"
            text += sheet_data.to_string(index=False)
        return text
    except Exception as e:
        print(f"Error reading Excel {file_path}: {e}")
        return ""


def extract_images_from_pdf(file_path):
    images = []
    try:
        doc = fitz.open(file_path)
        for page in doc:
            for img in page.get_images(full=True):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(BytesIO(image_bytes))
                images.append(image)
    except Exception as e:
        print(f"Error extracting images from PDF {file_path}: {e}")
    return images


def extract_text_from_image(image):
    try:
        return pytesseract.image_to_string(image)
    except Exception as e:
        print(f"Warning: Tesseract OCR failed: {e}")
        return ""


def process_document(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    extracted_text = ""

    try:
        if ext == ".pdf":
            extracted_text += extract_text_from_pdf(file_path)
            images = extract_images_from_pdf(file_path)
            for img in images:
                extracted_text += extract_text_from_image(img) + "\n"
        elif ext == ".docx":
            extracted_text += extract_text_from_docx(file_path)
        elif ext == ".txt":
            extracted_text += extract_text_from_txt(file_path)
        elif ext == ".xlsx":
            extracted_text += extract_text_from_excel(file_path)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return extracted_text.strip()


def chunk_text(text, chunk_size=500, overlap=50):
    """Splits text into chunks with overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def save_index():
    """Saves document data to JSON file."""
    global document_chunks, document_filenames
    if document_chunks:
        data = {
            'chunks': document_chunks,
            'filenames': document_filenames
        }
        try:
            with open(document_index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            print("Document index saved to disk.")
        except Exception as e:
            print(f"Error saving index: {e}")

def load_existing_index():
    """Loads existing document data from JSON."""
    global document_chunks, document_filenames
    if os.path.exists(document_index_file):
        try:
            with open(document_index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            document_chunks = data.get('chunks', [])
            document_filenames = data.get('filenames', [])
            print(f"Loaded existing document index with {len(document_filenames)} chunks.")
            return True
        except Exception as e:
            print(f"Failed to load document index: {e}")
            return False
    return False


def simple_keyword_score(query, text):
    """
    Simple keyword matching score.
    Returns number of query words found in text (case-insensitive).
    """
    query_words = query.lower().split()
    text_lower = text.lower()
    
    score = 0
    for word in query_words:
        # Count occurrences of each query word
        score += text_lower.count(word)
    
    return score


def add_document_to_store(file_path):
    """Add a document to the search index."""
    # Check if already indexed
    if file_path in document_filenames:
        return f"{file_path} is already indexed."

    text = process_document(file_path)
    if text:
        chunks = chunk_text(text)
        if not chunks:
             return f"{file_path} has no extractable content"
             
        # Add to storage
        document_chunks.extend(chunks)
        document_filenames.extend([file_path] * len(chunks))
        
        # Save immediately
        save_index()
        
        return f"{file_path} added ({len(chunks)} chunks)"
    return f"{file_path} has no extractable content"


def process_documents_from_folder(folder_path):
    """Process all documents in a folder."""
    if not os.path.exists(folder_path):
        return {"error": "Folder path doesn't exist!"}

    # Load existing index first
    load_existing_index()

    messages = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if filename.lower().endswith((".pdf", ".docx", ".txt", ".xlsx")):
            msg = add_document_to_store(file_path)
            messages.append(msg)

    if not messages:
        return {"error": "No supported document files found in folder."}

    return {"status": "success", "message": messages}


def search_documents(query, top_k=5):
    """
    Search documents using simple keyword matching.
    NO AI, NO SKLEARN, NO INTERNET - Just Python built-ins!
    """
    # Load if empty
    if not document_chunks:
        print("Document index empty, attempting to load from disk...")
        load_existing_index()

    if not document_chunks:
        return [{"error": "No documents indexed yet!"}]

    # Calculate scores for all chunks
    scores = []
    for i, chunk in enumerate(document_chunks):
        score = simple_keyword_score(query, chunk)
        scores.append((i, score))
    
    # Sort by score (highest first)
    scores.sort(key=lambda x: x[1], reverse=True)
    
    # Get top k results
    results = []
    for idx, score in scores[:top_k]:
        if score > 0:  # Only return chunks with at least one match
            results.append({
                "filename": document_filenames[idx],
                "snippet": document_chunks[idx][:200] + "...",
                "score": float(score)
            })

    if not results:
        return [{"error": "No matches found for your query"}]
    
    return results
