import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import UPLOAD_DIR, BASE_DIR
from app.schemas import BodyRecord, BodyCreate, GeminiKeyRequest
from app.database import get_db
from app.feature_extractor import get_feature_extractor
from app.bob_nlp import get_bob_nlp_engine

app = FastAPI(
    title="Post-Mortem Body Registry & Search (IBM Bob NLP)",
    description="A simple, streamlined system for uploading post-mortem body details, multi-image feature extraction, and IBM Bob NLP search.",
    version="3.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists and mount static files
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
async def startup_features():
    # Backfill extracted features for existing bodies that have images
    try:
        db = get_db()
        bodies = db.get_all_bodies()
        fe = get_feature_extractor()
        for b in bodies:
            if b.get("image_paths") and not b.get("extracted_features"):
                features = fe.extract_from_multiple_images(b["image_paths"])
                b["extracted_features"] = features
                db.save_body(b)
    except Exception as e:
        print(f"Feature backfill notice: {e}")


@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Body Registry API is running. UI file index.html not found."}


@app.get("/api/health")
async def health_check():
    db = get_db()
    bodies = db.get_all_bodies()
    return {
        "status": "operational",
        "system": "Post-Mortem Body Registry",
        "total_bodies": len(bodies)
    }


# ==========================================
# GEMINI CONFIGURATION & RE-EXTRACTION
# ==========================================
@app.get("/api/config/gemini-status", summary="Check if Google Gemini API key is configured")
async def get_gemini_status():
    from app.gemini_extractor import get_gemini_extractor
    gemini = get_gemini_extractor()
    is_conf = gemini.is_configured()
    masked = None
    if is_conf and gemini.api_key:
        masked = f"{gemini.api_key[:6]}...{gemini.api_key[-4:]}"
    return {
        "gemini_configured": is_conf,
        "model": gemini.model_name,
        "masked_key": masked
    }


@app.post("/api/config/gemini-key", summary="Set or update Google Gemini API key")
async def set_gemini_key(req: GeminiKeyRequest):
    if not req.api_key or len(req.api_key.strip()) < 8:
        raise HTTPException(status_code=400, detail="Invalid Gemini API key provided.")

    from app.gemini_extractor import get_gemini_extractor
    gemini = get_gemini_extractor()
    gemini.set_api_key(api_key=req.api_key, model_name=req.model_name)

    return {
        "status": "success",
        "message": f"Gemini API key successfully configured for model '{gemini.model_name}'.",
        "gemini_configured": True,
        "model": gemini.model_name
    }


@app.post("/api/bodies/{body_id}/re-extract", summary="Re-run multimodal visual feature extraction on an existing body record using Gemini")
async def re_extract_body_features(body_id: str):
    db = get_db()
    body = db.get_body(body_id)
    if not body:
        raise HTTPException(status_code=404, detail=f"Body record '{body_id}' not found.")

    image_paths = body.get("image_paths", [])
    if not image_paths:
        raise HTTPException(status_code=400, detail="This body record has no uploaded photos to analyze.")

    fe = get_feature_extractor()
    extracted = fe.extract_from_multiple_images(image_paths)

    body["extracted_features"] = extracted

    # If details was default or empty, update it
    if body.get("details") in ["No distinctive details recorded", ""] and extracted.get("summary"):
        body["details"] = extracted["summary"]

    if body.get("gender") == "Unknown" and extracted.get("suggested_gender") in ["Male", "Female"]:
        body["gender"] = extracted["suggested_gender"]

    db.save_body(body)
    return {
        "status": "success",
        "message": f"Features successfully re-extracted for body {body_id}.",
        "body": body
    }


# ==========================================
# MULTI-IMAGE FEATURE EXTRACTION
# ==========================================
@app.post("/api/extract-features", summary="Extract visual forensic features from multiple uploaded photos")
async def extract_features_preview(
    images: List[UploadFile] = File(..., description="Multiple photos of body, clothing, or belongings")
):
    if not images:
        raise HTTPException(status_code=400, detail="No images provided for feature extraction.")

    temp_paths = []
    temp_dir = UPLOAD_DIR / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        fe = get_feature_extractor()
        for idx, file in enumerate(images):
            if file and file.filename:
                ext = Path(file.filename).suffix or ".jpg"
                temp_file = temp_dir / f"temp_{uuid.uuid4().hex[:6]}_{idx}{ext}"
                contents = await file.read()
                with open(temp_file, "wb") as f:
                    f.write(contents)
                temp_paths.append(str(temp_file))

        extracted = fe.extract_from_multiple_images(temp_paths)
        return extracted
    finally:
        # Clean up temporary files
        for p in temp_paths:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass


# ==========================================
# BOB NLP SEARCH & BODIES WORKFLOW
# ==========================================
@app.get("/api/nlp-search", summary="IBM Bob NLP natural language search with semantic parsing & forensic rationale")
async def nlp_search_bodies(
    q: str = Query(..., description="Natural language search query e.g. 'find male body in bilaspur wearing white clothes'"),
    top_k: int = Query(20, description="Max results to return")
):
    bob = get_bob_nlp_engine()
    return bob.search(query=q, top_k=top_k)


@app.get("/api/bodies", response_model=List[BodyRecord], summary="Search and list post-mortem body records with optional Bob NLP")
async def list_or_search_bodies(
    q: Optional[str] = Query(None, description="Search query across ID, tag, location, clothing, marks, and notes"),
    gender: Optional[str] = Query(None, description="Filter by gender (Male, Female, Unknown)"),
    nlp: Optional[bool] = Query(False, description="Enable IBM Bob NLP semantic search")
):
    db = get_db()
    if not q or not q.strip():
        return db.search_bodies(query=None, gender=gender)

    if nlp:
        bob = get_bob_nlp_engine()
        search_res = bob.search(query=q.strip())
        results = []
        g_filter = (gender or "").strip().lower()
        for item in search_res.get("results", []):
            b = item["body"]
            if g_filter and g_filter != "all":
                if g_filter not in str(b.get("gender", "")).lower():
                    continue
            b_copy = dict(b)
            b_copy["nlp_score"] = item.get("nlp_score")
            b_copy["nlp_rationale"] = item.get("nlp_rationale")
            results.append(b_copy)
        return results

    return db.search_bodies(query=q, gender=gender)


@app.post("/api/bodies", response_model=BodyRecord, summary="Upload post-mortem body record with minimal details and multi-image feature extraction")
async def upload_body(
    tag: Optional[str] = Form(None, description="Optional custom tag or identifier e.g. 'Body #12'"),
    location: Optional[str] = Form("", description="Location found (e.g. Bilaspur, Coach B4)"),
    gender: Optional[str] = Form("Unknown", description="Gender (Male, Female, Unknown)"),
    age: Optional[str] = Form(None, description="Estimated age or age range"),
    details: Optional[str] = Form("", description="Identifying details (clothing, marks, scars, belongings, notes)"),
    images: List[UploadFile] = File([], description="Multiple photos of the body or personal belongings")
):
    db = get_db()
    
    # Generate clean ID
    clean_tag = tag.strip() if tag and tag.strip() else ""
    body_id = f"PM-{uuid.uuid4().hex[:6].upper()}"

    saved_images = []
    for idx, file in enumerate(images):
        if file and file.filename:
            ext = Path(file.filename).suffix or ".jpg"
            filename = f"{body_id.lower()}_img_{idx+1}{ext}"
            file_path = UPLOAD_DIR / filename
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)
            saved_images.append(f"/static/uploads/{filename}")

    # Extract forensic features across all uploaded images
    extracted_features = None
    if saved_images:
        try:
            fe = get_feature_extractor()
            extracted_features = fe.extract_from_multiple_images(saved_images)
        except Exception as e:
            print(f"Feature extraction notice for body {body_id}: {e}")

    # Infer or suggest gender if left Unknown
    final_gender = gender.strip() if gender and gender.strip() else "Unknown"
    if final_gender == "Unknown" and extracted_features:
        sug_g = extracted_features.get("suggested_gender")
        if sug_g and sug_g in ["Male", "Female"]:
            final_gender = sug_g

    # Enrich details if empty or augment with extracted features
    final_details = details.strip() if details and details.strip() else ""
    if not final_details:
        if extracted_features and extracted_features.get("summary"):
            final_details = extracted_features["summary"]
        else:
            final_details = "No distinctive details recorded"

    record = {
        "id": body_id,
        "tag": clean_tag if clean_tag else body_id,
        "location": location.strip() if location and location.strip() else "Unspecified Location",
        "gender": final_gender,
        "age": age.strip() if age and age.strip() else None,
        "details": final_details,
        "image_paths": saved_images,
        "created_at": datetime.utcnow().isoformat(),
        "status": "Unidentified",
        "extracted_features": extracted_features
    }

    db.save_body(record)
    return record


@app.get("/api/bodies/{body_id}", response_model=BodyRecord, summary="Get details of a specific body")
async def get_body(body_id: str):
    db = get_db()
    body = db.get_body(body_id)
    if not body:
        raise HTTPException(status_code=404, detail=f"Body record '{body_id}' not found.")
    return body


@app.delete("/api/bodies/{body_id}", summary="Delete a body record")
async def delete_body(body_id: str):
    db = get_db()
    body = db.get_body(body_id)
    if not body:
        raise HTTPException(status_code=404, detail=f"Body record '{body_id}' not found.")

    # Remove files if exist
    for img_path in body.get("image_paths", []):
        try:
            rel = img_path.replace("/static/uploads/", "")
            target_path = UPLOAD_DIR / rel
            if target_path.exists() and target_path.is_file():
                target_path.unlink()
        except Exception:
            pass

    db.delete_body(body_id)
    return {"status": "success", "message": f"Body {body_id} successfully deleted."}


# ==========================================
# BACKWARD COMPATIBILITY ENDPOINTS
# ==========================================
@app.get("/api/post-mortem")
async def list_post_mortem(
    q: Optional[str] = Query(None),
    gender: Optional[str] = Query(None)
):
    db = get_db()
    return db.search_bodies(query=q, gender=gender)


@app.post("/api/post-mortem")
async def legacy_log_post_mortem(
    recovery_location: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    estimated_gender: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    estimated_age_range: Optional[str] = Form(None),
    age: Optional[str] = Form(None),
    clothing_recovered: Optional[str] = Form(None),
    scars_and_birthmarks: Optional[str] = Form(None),
    hair_observation: Optional[str] = Form(None),
    jewelry_belongings: Optional[str] = Form(None),
    details: Optional[str] = Form(None),
    tag: Optional[str] = Form(None),
    custom_id: Optional[str] = Form(None),
    images: List[UploadFile] = File([])
):
    # Consolidate whichever fields were passed
    loc = location or recovery_location or "Unspecified Location"
    gen = gender or estimated_gender or "Unknown"
    ag = age or estimated_age_range or None
    tg = tag or custom_id or None

    parts = []
    if details:
        parts.append(details)
    if clothing_recovered:
        parts.append(f"Clothing: {clothing_recovered}")
    if scars_and_birthmarks and scars_and_birthmarks.strip().lower() != "no":
        parts.append(f"Scars/Marks: {scars_and_birthmarks}")
    if hair_observation:
        parts.append(f"Hair: {hair_observation}")
    if jewelry_belongings:
        parts.append(f"Belongings: {jewelry_belongings}")

    det = " | ".join(parts) if parts else "No distinctive details recorded"

    return await upload_body(tag=tg, location=loc, gender=gen, age=ag, details=det, images=images)


@app.get("/api/post-mortem/{pm_id}")
async def get_legacy_pm(pm_id: str):
    return await get_body(pm_id)
