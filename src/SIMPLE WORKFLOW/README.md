# 🗂️ Post-Mortem Body Registry & IBM Bob NLP Search

A simple, fast, and lightweight system for logging post-mortem recovery details with multi-image intake, automatic visual feature extraction, and **IBM Bob NLP conversational natural language search**.

---

## 🌟 Key Capabilities

1. **🧠 IBM Bob NLP Conversational Search Engine:**
   - Ask natural language questions or describe persons in full sentences instead of rigid keywords:
     - *"find male body found in bilaspur wearing white clothes"*
     - *"who was found at nfsu with blue jeans?"*
     - *"bodies wearing maroon kurta or red clothing"*
     - *"victims with wristwatch or sacred kalawa thread"*
   - **Intent & Entity Parsing:** Automatically extracts gender, recovery locations, clothing types, accessories, and physical traits from natural text.
   - **Multimodal Semantic Vector Matching:** Evaluates query embeddings against multimodal visual and text embeddings.
   - **Calibrated Match Score & Forensic Rationale:** Surfaces results with confidence percentages (e.g. `🎯 96% Bob Match`) and explanations (`💡 Gender matched (Male) • Location matched 'bilaspur' • Traits: white, shirt`).

2. **Multi-Image Intake per Body:**
   - Upload multiple reference photos per record (face, clothing, scars, tattoos, jewelry, belongings).
   - Previews all selected images with live thumbnails and image removal options before saving.

3. **AI Visual Feature Extraction (OpenAI CLIP + CV Palette Engine):**
   - Automatically analyzes all uploaded photos across clothing, accessories, marks, and dominant color palette.
   - **"Auto-Extract Features" Button:** Preview extracted features in real time before submitting and apply them directly into the description notes.
   - **Integrated Search Indexing:** Extracted features are indexed and searchable by the Bob NLP engine.

4. **Clean Visual Body Cards & Details:**
   - Responsive cards with photo thumbnail indicators for multiple photos.
   - Displays Bob NLP relevance match badges and rationales.
   - Click "Details" to open a full modal with high-resolution photos, complete notes, and forensic analysis.

---

## 🚀 Quickstart

### 1. Start the Server
```powershell
.\venv\Scripts\python run.py
```

### 2. Access the Application
- **🖥️ Web Application:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **📑 Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🧪 Run Tests
```powershell
.\venv\Scripts\python test_backend.py
```

---

## 📡 REST API Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health status and total count of bodies |
| `GET` | `/api/nlp-search` | **IBM Bob NLP conversational search (`?q=...`)** |
| `GET` | `/api/bodies` | Search and list bodies (`?q=keyword&nlp=true&gender=Male`) |
| `POST` | `/api/bodies` | Upload body with multiple images and auto feature extraction |
| `POST` | `/api/extract-features` | Extract visual features preview from multiple uploaded photos |
| `GET` | `/api/bodies/{id}` | Get specific body details including extracted features |
| `DELETE` | `/api/bodies/{id}` | Delete body record and associated images |
