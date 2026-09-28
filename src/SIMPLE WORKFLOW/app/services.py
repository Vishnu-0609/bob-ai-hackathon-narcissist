import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from PIL import Image
import numpy as np
from fastapi import UploadFile, HTTPException

from app.config import UPLOAD_DIR
from app.model import get_clip_model
from app.database import get_db
from app.schemas import PersonResponse, SearchMatch, SearchResponse

class PersonService:
    def __init__(self):
        self.clip = get_clip_model()
        self.db = get_db()

    async def register_person(
        self,
        name: str,
        gender: str,
        hair_color: str,
        clothing: str,
        other_characteristics: Optional[str],
        images: List[UploadFile]
    ) -> PersonResponse:
        if not images or len(images) < 1:
            raise HTTPException(status_code=400, detail="At least 1 picture is required (recommended 2-3).")

        person_id = str(uuid.uuid4())[:8]
        person_upload_dir = UPLOAD_DIR / person_id
        person_upload_dir.mkdir(parents=True, exist_ok=True)

        saved_image_paths = []
        image_embeddings = []

        # 1. Save images and compute image CLIP embeddings
        for idx, file in enumerate(images):
            # Check content type
            if file.content_type and not file.content_type.startswith("image/"):
                continue

            file_ext = Path(file.filename).suffix if file.filename else ".jpg"
            if not file_ext:
                file_ext = ".jpg"
            image_filename = f"img_{idx+1}{file_ext}"
            file_path = person_upload_dir / image_filename

            # Save uploaded bytes to file
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)

            # Generate CLIP embedding for the image
            try:
                embedding = self.clip.encode_image(file_path)
                image_embeddings.append(embedding)
                # Store relative path for API serving
                relative_path = f"/static/uploads/{person_id}/{image_filename}"
                saved_image_paths.append(relative_path)
            except Exception as e:
                print(f"Error processing image {file.filename}: {e}")

        if not saved_image_paths:
            shutil.rmtree(person_upload_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail="Failed to process uploaded images. Ensure they are valid image files.")

        # 2. Generate descriptive text embedding representing all characteristics
        profile_text = (
            f"A photo of {name}, {gender}, with {hair_color} hair, wearing {clothing}."
        )
        if other_characteristics and other_characteristics.strip():
            profile_text += f" Features: {other_characteristics.strip()}."

        profile_embedding = self.clip.encode_text(profile_text)

        # 3. Compute a composite person vector (mean of images + profile text)
        all_vecs = np.array(image_embeddings + [profile_embedding])
        composite_vec = np.mean(all_vecs, axis=0)
        norm = np.linalg.norm(composite_vec)
        if norm > 0:
            composite_vec = (composite_vec / norm).tolist()
        else:
            composite_vec = profile_embedding

        # 4. Prepare data for ChromaDB upsert
        ids = []
        embeddings = []
        metadatas = []
        documents = []

        # Insert individual image vectors
        for i, (emb, img_path) in enumerate(zip(image_embeddings, saved_image_paths)):
            doc_id = f"{person_id}_img_{i}"
            ids.append(doc_id)
            embeddings.append(emb)
            metadatas.append({
                "person_id": person_id,
                "name": name,
                "gender": gender.lower().strip(),
                "hair_color": hair_color.lower().strip(),
                "clothing": clothing.strip(),
                "other_characteristics": (other_characteristics or "").strip(),
                "item_type": "image",
                "image_path": img_path
            })
            documents.append(f"{name} photo {i+1} ({gender}, {hair_color} hair, {clothing})")

        # Insert profile text vector
        ids.append(f"{person_id}_profile")
        embeddings.append(profile_embedding)
        metadatas.append({
            "person_id": person_id,
            "name": name,
            "gender": gender.lower().strip(),
            "hair_color": hair_color.lower().strip(),
            "clothing": clothing.strip(),
            "other_characteristics": (other_characteristics or "").strip(),
            "item_type": "profile",
            "image_path": saved_image_paths[0]
        })
        documents.append(profile_text)

        # Insert composite vector
        ids.append(f"{person_id}_composite")
        embeddings.append(composite_vec)
        metadatas.append({
            "person_id": person_id,
            "name": name,
            "gender": gender.lower().strip(),
            "hair_color": hair_color.lower().strip(),
            "clothing": clothing.strip(),
            "other_characteristics": (other_characteristics or "").strip(),
            "item_type": "composite",
            "image_path": saved_image_paths[0]
        })
        documents.append(f"Composite embedding of {name}")

        self.db.insert_vectors(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

        # 5. Save structured person record
        created_at = datetime.utcnow().isoformat()
        person_record = {
            "id": person_id,
            "name": name,
            "gender": gender,
            "hair_color": hair_color,
            "clothing": clothing,
            "other_characteristics": other_characteristics,
            "image_paths": saved_image_paths,
            "created_at": created_at
        }
        self.db.save_person_record(person_id, person_record)

        return PersonResponse(**person_record)

    def search_by_text(
        self,
        query: str,
        gender_filter: Optional[str] = None,
        hair_color_filter: Optional[str] = None,
        top_k: int = 10
    ) -> SearchResponse:
        # Encode query text using CLIP
        query_vector = self.clip.encode_text(query)
        return self._search_vector(query_vector, query_label=query, gender_filter=gender_filter, hair_color_filter=hair_color_filter, top_k=top_k)

    def search_by_image(
        self,
        image_file: UploadFile,
        gender_filter: Optional[str] = None,
        hair_color_filter: Optional[str] = None,
        top_k: int = 10
    ) -> SearchResponse:
        image = Image.open(image_file.file).convert("RGB")
        query_vector = self.clip.encode_image(image)
        return self._search_vector(query_vector, query_label="Visual Search (Image Query)", gender_filter=gender_filter, hair_color_filter=hair_color_filter, top_k=top_k)

    def _build_where_filter(self, gender_filter: Optional[str], hair_color_filter: Optional[str]) -> Optional[Dict[str, Any]]:
        conditions = []
        if gender_filter and gender_filter.strip() and gender_filter.strip().lower() != "all":
            conditions.append({"gender": gender_filter.strip().lower()})
        if hair_color_filter and hair_color_filter.strip() and hair_color_filter.strip().lower() != "all":
            conditions.append({"hair_color": hair_color_filter.strip().lower()})

        if len(conditions) == 0:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}

    def _search_vector(
        self,
        query_vector: List[float],
        query_label: str,
        gender_filter: Optional[str],
        hair_color_filter: Optional[str],
        top_k: int
    ) -> SearchResponse:
        where_filter = self._build_where_filter(gender_filter, hair_color_filter)
        raw_results = self.db.query_vectors(query_vector, n_results=top_k * 4, where_filter=where_filter)

        ids = raw_results.get("ids", [[]])[0]
        distances = raw_results.get("distances", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0]

        # Aggregate by person_id
        # In cosine distance: dist = 1 - cos_sim, so cos_sim = 1 - dist
        person_matches: Dict[str, Dict[str, Any]] = {}

        for doc_id, dist, meta in zip(ids, distances, metadatas):
            pid = meta["person_id"]
            # Convert cosine distance to cosine similarity percentage score [0, 1]
            similarity = max(0.0, min(1.0, 1.0 - dist))

            if pid not in person_matches:
                person_matches[pid] = {
                    "max_similarity": similarity,
                    "matched_image_path": meta.get("image_path"),
                    "matched_type": meta.get("item_type", "image"),
                    "metadata": meta
                }
            else:
                if similarity > person_matches[pid]["max_similarity"]:
                    person_matches[pid]["max_similarity"] = similarity
                    if meta.get("image_path"):
                        person_matches[pid]["matched_image_path"] = meta.get("image_path")
                    person_matches[pid]["matched_type"] = meta.get("item_type", "image")

        # Rank persons by highest similarity score
        sorted_pids = sorted(
            person_matches.keys(),
            key=lambda p: person_matches[p]["max_similarity"],
            reverse=True
        )[:top_k]

        results: List[SearchMatch] = []
        for pid in sorted_pids:
            match_data = person_matches[pid]
            person_rec = self.db.get_person_record(pid)
            if not person_rec:
                # Fallback to metadata
                meta = match_data["metadata"]
                person_rec = {
                    "id": pid,
                    "name": meta.get("name", "Unknown"),
                    "gender": meta.get("gender", ""),
                    "hair_color": meta.get("hair_color", ""),
                    "clothing": meta.get("clothing", ""),
                    "other_characteristics": meta.get("other_characteristics", ""),
                    "image_paths": [meta.get("image_path")] if meta.get("image_path") else []
                }

            results.append(SearchMatch(
                person_id=pid,
                name=person_rec["name"],
                gender=person_rec["gender"],
                hair_color=person_rec["hair_color"],
                clothing=person_rec["clothing"],
                other_characteristics=person_rec.get("other_characteristics"),
                similarity_score=round(match_data["max_similarity"], 4),
                matched_image_path=match_data.get("matched_image_path") or (person_rec["image_paths"][0] if person_rec.get("image_paths") else None),
                all_image_paths=person_rec.get("image_paths", []),
                matched_type=match_data.get("matched_type", "image")
            ))

        return SearchResponse(
            query=query_label,
            total_results=len(results),
            results=results
        )

    def get_all_persons(self) -> List[PersonResponse]:
        records = self.db.get_all_persons()
        return [PersonResponse(**r) for r in records]

    def get_person(self, person_id: str) -> Optional[PersonResponse]:
        record = self.db.get_person_record(person_id)
        if record:
            return PersonResponse(**record)
        return None

    def delete_person(self, person_id: str) -> bool:
        record = self.db.get_person_record(person_id)
        if not record:
            return False

        # Delete vectors
        self.db.delete_vectors_by_person_id(person_id)

        # Delete database record
        self.db.delete_person_record(person_id)

        # Delete uploaded files
        person_dir = UPLOAD_DIR / person_id
        if person_dir.exists():
            shutil.rmtree(person_dir, ignore_errors=True)

        return True

_service_instance = None

def get_person_service() -> PersonService:
    global _service_instance
    if _service_instance is None:
        _service_instance = PersonService()
    return _service_instance
