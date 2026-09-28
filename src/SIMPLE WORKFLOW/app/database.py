import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.config import DATA_DIR, UPLOAD_DIR

BODIES_FILE = DATA_DIR / "bodies.json"
PM_FILE = DATA_DIR / "post_mortem.json"

class SimpleDatabase:
    _instance = None

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_storage()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_storage(self):
        """Initializes bodies.json and migrates any existing post_mortem.json data."""
        if not BODIES_FILE.exists():
            initial_data = {}
            if PM_FILE.exists():
                try:
                    with open(PM_FILE, "r", encoding="utf-8") as f:
                        pm_data = json.load(f)
                    for k, v in pm_data.items():
                        norm = self._normalize_legacy_record(v)
                        initial_data[norm["id"]] = norm
                except Exception as e:
                    print(f"Error migrating post_mortem.json: {e}")
            with open(BODIES_FILE, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

    def _normalize_legacy_record(self, pm_data: Dict[str, Any]) -> Dict[str, Any]:
        body_id = pm_data.get("id") or pm_data.get("custom_id") or f"PM-{uuid.uuid4().hex[:6].upper()}"
        tag = pm_data.get("custom_id") or body_id
        location = pm_data.get("recovery_location", "")
        gender = pm_data.get("estimated_gender", "Unknown")
        age = pm_data.get("estimated_age_range")

        parts = []
        if pm_data.get("details"):
            parts.append(pm_data["details"])
        if pm_data.get("clothing_recovered"):
            parts.append(f"Clothing: {pm_data['clothing_recovered']}")
        if pm_data.get("scars_and_birthmarks") and str(pm_data["scars_and_birthmarks"]).strip().lower() != "no":
            parts.append(f"Marks/Scars: {pm_data['scars_and_birthmarks']}")
        if pm_data.get("tattoos_piercings"):
            parts.append(f"Tattoos: {pm_data['tattoos_piercings']}")
        if pm_data.get("jewelry_belongings"):
            parts.append(f"Belongings: {pm_data['jewelry_belongings']}")
        if pm_data.get("hair_observation"):
            parts.append(f"Hair: {pm_data['hair_observation']}")
        if pm_data.get("dental_observations"):
            parts.append(f"Dental: {pm_data['dental_observations']}")

        details_str = " | ".join(parts) if parts else "No distinctive details recorded"

        return {
            "id": body_id,
            "tag": tag,
            "location": location,
            "gender": gender,
            "age": str(age) if age else None,
            "details": details_str,
            "image_paths": pm_data.get("image_paths", []),
            "created_at": pm_data.get("created_at", datetime.utcnow().isoformat()),
            "status": pm_data.get("status", "Unidentified"),
            "extracted_features": pm_data.get("extracted_features")
        }

    def _load_bodies(self) -> Dict[str, Any]:
        if not BODIES_FILE.exists():
            return {}
        try:
            with open(BODIES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_bodies(self, data: Dict[str, Any]):
        with open(BODIES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_body(self, body_data: Dict[str, Any]):
        bodies = self._load_bodies()
        bodies[body_data["id"]] = body_data
        self._save_bodies(bodies)

        # Also sync to post_mortem.json for backward compatibility
        try:
            pm_dict = {}
            if PM_FILE.exists():
                with open(PM_FILE, "r", encoding="utf-8") as f:
                    pm_dict = json.load(f)
            pm_dict[body_data["id"]] = {
                "id": body_data["id"],
                "custom_id": body_data.get("tag", body_data["id"]),
                "recovery_location": body_data.get("location", ""),
                "estimated_gender": body_data.get("gender", "Unknown"),
                "estimated_age_range": body_data.get("age", ""),
                "clothing_recovered": body_data.get("details", ""),
                "scars_and_birthmarks": "",
                "hair_observation": "",
                "details": body_data.get("details", ""),
                "image_paths": body_data.get("image_paths", []),
                "created_at": body_data.get("created_at", datetime.utcnow().isoformat()),
                "status": body_data.get("status", "Unidentified"),
                "extracted_features": body_data.get("extracted_features")
            }
            with open(PM_FILE, "w", encoding="utf-8") as f:
                json.dump(pm_dict, f, indent=2)
        except Exception as e:
            print(f"Warning syncing post_mortem.json: {e}")

    def get_body(self, body_id: str) -> Optional[Dict[str, Any]]:
        bodies = self._load_bodies()
        return bodies.get(body_id)

    def get_all_bodies(self) -> List[Dict[str, Any]]:
        bodies = self._load_bodies()
        body_list = list(bodies.values())
        # Sort newest first
        body_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return body_list

    def delete_body(self, body_id: str) -> bool:
        bodies = self._load_bodies()
        if body_id in bodies:
            del bodies[body_id]
            self._save_bodies(bodies)
            # Remove from PM file as well
            if PM_FILE.exists():
                try:
                    with open(PM_FILE, "r", encoding="utf-8") as f:
                        pm_dict = json.load(f)
                    if body_id in pm_dict:
                        del pm_dict[body_id]
                        with open(PM_FILE, "w", encoding="utf-8") as f:
                            json.dump(pm_dict, f, indent=2)
                except Exception:
                    pass
            return True
        return False

    def search_bodies(self, query: Optional[str] = None, gender: Optional[str] = None) -> List[Dict[str, Any]]:
        all_bodies = self.get_all_bodies()
        filtered = []

        q = (query or "").strip().lower()
        g_filter = (gender or "").strip().lower()

        for body in all_bodies:
            # Gender filter
            body_gender = str(body.get("gender", "")).lower()
            if g_filter and g_filter != "all":
                if g_filter not in body_gender:
                    continue

            # Query filter (matches ID, tag, location, details, age, and AI extracted features)
            if q:
                # Extract text representations from extracted_features
                ef_texts = []
                ef = body.get("extracted_features") or {}
                if isinstance(ef, dict):
                    if ef.get("summary"):
                        ef_texts.append(ef["summary"])
                    for c in ef.get("detected_clothing", []):
                        ef_texts.append(c.get("name", "") if isinstance(c, dict) else str(c))
                    for a in ef.get("detected_accessories", []):
                        ef_texts.append(a.get("name", "") if isinstance(a, dict) else str(a))
                    for m in ef.get("detected_marks", []):
                        ef_texts.append(m.get("name", "") if isinstance(m, dict) else str(m))
                    for col in ef.get("detected_colors", []):
                        ef_texts.append(col.get("name", "") if isinstance(col, dict) else str(col))

                searchable_text = " ".join([
                    str(body.get("id", "")),
                    str(body.get("tag", "")),
                    str(body.get("location", "")),
                    str(body.get("gender", "")),
                    str(body.get("age", "")),
                    str(body.get("details", "")),
                    " ".join(ef_texts)
                ]).lower()

                # Split query into words to allow multi-word search (e.g. 'male bilaspur')
                q_tokens = q.split()
                if not all(tok in searchable_text for tok in q_tokens):
                    continue

            filtered.append(body)

        return filtered


# Backward compatibility wrapper for legacy DVIDatabase references
class LegacyDVIWrapper:
    def __init__(self, db: SimpleDatabase):
        self.db = db

    def get_all_pm(self):
        bodies = self.db.get_all_bodies()
        from app.schemas import PostMortemRecord
        records = []
        for b in bodies:
            records.append(PostMortemRecord(
                id=b["id"],
                custom_id=b.get("tag", b["id"]),
                recovery_location=b.get("location", "Unknown Location"),
                estimated_gender=b.get("gender", "Unknown"),
                estimated_age_range=b.get("age") or "Adult",
                hair_observation="",
                scars_and_birthmarks="",
                clothing_recovered=b.get("details", ""),
                image_paths=b.get("image_paths", []),
                created_at=b.get("created_at", datetime.utcnow().isoformat()),
                status=b.get("status", "Unidentified")
            ))
        return records

    def get_pm(self, pm_id: str):
        b = self.db.get_body(pm_id)
        if not b:
            return None
        from app.schemas import PostMortemRecord
        return PostMortemRecord(
            id=b["id"],
            custom_id=b.get("tag", b["id"]),
            recovery_location=b.get("location", "Unknown Location"),
            estimated_gender=b.get("gender", "Unknown"),
            estimated_age_range=b.get("age") or "Adult",
            hair_observation="",
            scars_and_birthmarks="",
            clothing_recovered=b.get("details", ""),
            image_paths=b.get("image_paths", []),
            created_at=b.get("created_at", datetime.utcnow().isoformat()),
            status=b.get("status", "Unidentified")
        )

    def save_pm(self, record):
        body_data = {
            "id": getattr(record, "id", str(uuid.uuid4())[:8]),
            "tag": getattr(record, "custom_id", None) or getattr(record, "id", ""),
            "location": getattr(record, "recovery_location", ""),
            "gender": getattr(record, "estimated_gender", "Unknown"),
            "age": getattr(record, "estimated_age_range", None),
            "details": getattr(record, "clothing_recovered", ""),
            "image_paths": getattr(record, "image_paths", []),
            "created_at": getattr(record, "created_at", datetime.utcnow().isoformat()),
            "status": getattr(record, "status", "Unidentified")
        }
        self.db.save_body(body_data)

    def get_all_am(self):
        return []

    def get_am(self, am_id: str):
        return None

    def get_reconciliation_record(self, pm_id: str):
        return None

    def save_reconciliation_record(self, pm_id: str, data: dict):
        pass


def get_db() -> SimpleDatabase:
    return SimpleDatabase.get_instance()

def get_dvi_db() -> LegacyDVIWrapper:
    return LegacyDVIWrapper(SimpleDatabase.get_instance())
