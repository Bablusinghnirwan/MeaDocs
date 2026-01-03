# 📂 MeaDocs – AI-Powered Multimedia Search  

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)  
[![Flask](https://img.shields.io/badge/Backend-Flask-lightgreen.svg)](https://flask.palletsprojects.com/)  
[![Flutter](https://img.shields.io/badge/Frontend-Flutter-blue.svg)](https://flutter.dev/)  

> **Your Personal AI Librarian** – Search **images, videos, documents, and audio** on your device using natural language queries.  
> Privacy-first. Offline. Fast. Smart.  

---

## ✨ Features  

- 🔍 **Natural Language Search** – Search by typing descriptions like *"Show me the photo where I and Jaya were standing outside my house"*.  
- 🖼️ **Image Search** – AI-based photo retrieval with **OpenAI CLIP embeddings**.  
- 🎥 **Video Search** – Find clips based on objects, actions, and visual context.  
- 📄 **Document Search** – Locate PDFs, Word files, or text documents by content.  
- 🎙️ **Audio Search** – Identify and search spoken words inside audio files.  
- ⚡ **FAISS-powered Search** – Ultra-fast vector similarity matching.  
- 📱 **Mobile Ready** – Fully integrated with a **Flutter Android app**.  
- 🔐 **Privacy First** – Works **offline**, data never leaves your device.  

---

## 🛠️ Tech Stack  

- **Backend**: [Python](https://www.python.org/), [Flask](https://flask.palletsprojects.com/)  
- **AI Models**: [OpenAI CLIP](https://github.com/openai/CLIP) (images/videos), Whisper/STT (audio)  
- **Vector Database**: [FAISS](https://github.com/facebookresearch/faiss)  
- **Frontend**: [Flutter](https://flutter.dev/) (mobile), HTML/CSS (prototype)  
- **Database**: SQLite (for metadata & tagging)  

---

## 📂 Project Structure  

```bash
MeaDocs/
│── backend/           # Flask backend for AI-powered search
│   ├── app.py         # Main Flask API
│   ├── utils/         # Helper scripts (encoding, preprocessing)
│   └── models/        # Pre-trained AI models
│
│── frontend/          # Flutter mobile app
│   ├── lib/           # Dart source code
│   └── assets/        # UI assets
│
│── data/              # Sample dataset (images, videos, docs, audio)
│── docs/              # Documentation files
│── Template/          # Boilerplate templates
│── requirements.txt   # Python dependencies
│── README.md          # Project description

```

---

## ⚙️ Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/MeaDocs.git
cd MeaDocs
```

### 2. Create & activate virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the backend
```bash
cd backend
python app.py
Backend will be live at: http://localhost:5000
```

---

## 🔍 Usage  

1. Open the **Flutter app / frontend**.  
2. Select media type (**Photo, Video, Document, Audio**).  
3. Enter or speak your query.  
4. MeaDocs instantly retrieves the most relevant files.  

---

## 🔮 Roadmap  

- [x] **Image search** (CLIP + FAISS)  
- [x] **Video search**  
- [x] **Document search**  
- [ ] **Audio search** (offline STT)  
- [ ] **Entity & context recognition** (people, places, relationships)  
- [ ] **Optimized mobile integration**  
- [ ] **Android app release** on Play Store  

---

## 🤝 Contributing  

We ❤️ contributions!  

1. Fork this repo  
2. Create a new branch (`feature/your-feature`)  
3. Commit your changes  
4. Open a Pull Request 🚀  
