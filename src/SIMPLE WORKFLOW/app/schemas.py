from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ==========================================
# SIMPLIFIED BODY MODELS
# ==========================================
class BodyCreate(BaseModel):
    tag: Optional[str] = Field(None, description="Optional body identifier or tag (e.g. Body #1)")
    location: Optional[str] = Field("", description="Location found (e.g. Bilaspur, Coach B4)")
    gender: Optional[str] = Field("Unknown", description="Gender (Male, Female, Unknown)")
    age: Optional[str] = Field(None, description="Estimated age or age range")
    details: Optional[str] = Field("", description="Identifying details (clothing, marks, scars, belongings)")

class BodyRecord(BaseModel):
    id: str
    tag: str
    location: str
    gender: str
    age: Optional[str] = None
    details: str
    image_paths: List[str] = []
    created_at: str
    status: str = "Unidentified"
    extracted_features: Optional[Dict[str, Any]] = None
    nlp_score: Optional[float] = None
    nlp_rationale: Optional[str] = None

class GeminiKeyRequest(BaseModel):
    api_key: str = Field(..., description="Google Gemini API key")
    model_name: Optional[str] = Field("gemini-2.5-flash", description="Gemini model name (e.g. gemini-2.5-flash, gemini-2.0-flash)")


# ==========================================
# LEGACY COMPATIBILITY MODELS (DVI / Interpol)
# ==========================================
class AnteMortemProfile(BaseModel):
    id: str
    custom_id: Optional[str] = None
    full_name: str = ""
    reported_by: Optional[str] = None
    contact_phone: Optional[str] = None
    gender: str = "Unknown"
    age: Optional[int] = None
    age_range: Optional[str] = None
    height_cm: Optional[float] = None
    hair_description: str = ""
    scars_and_birthmarks: str = ""
    tattoos_piercings: Optional[str] = None
    clothing_worn: str = ""
    jewelry_accessories: Optional[str] = None
    dental_notes: Optional[str] = None
    other_observations: Optional[str] = None
    image_paths: List[str] = []
    created_at: str = ""
    status: str = "Active_Searching"

class PostMortemRecord(BaseModel):
    id: str
    custom_id: Optional[str] = None
    recovery_location: str = ""
    mortuary_facility: Optional[str] = None
    estimated_gender: str = "Unknown"
    estimated_age_range: str = ""
    estimated_height_cm: Optional[float] = None
    hair_observation: str = ""
    scars_and_birthmarks: str = ""
    tattoos_piercings: Optional[str] = None
    clothing_recovered: str = ""
    jewelry_belongings: Optional[str] = None
    dental_observations: Optional[str] = None
    pathology_notes: Optional[str] = None
    image_paths: List[str] = []
    created_at: str = ""
    status: str = "Unidentified"
    confirmed_am_id: Optional[str] = None

class MatchCandidate(BaseModel):
    rank: int = 1
    ante_mortem_id: str = ""
    missing_person_name: str = ""
    match_probability: float = 0.0
    visual_clip_similarity: float = 0.0
    semantic_clip_similarity: float = 0.0
    biometric_score: float = 0.0
    rationale: str = ""
    matching_factors: List[str] = []
    discrepancy_flags: List[str] = []
    am_profile: Optional[AnteMortemProfile] = None
    best_am_image: Optional[str] = None
    best_pm_image: Optional[str] = None

class BodyReconciliation(BaseModel):
    post_mortem_id: str
    post_mortem_record: Optional[PostMortemRecord] = None
    top_candidates: List[MatchCandidate] = []
    generated_at: str = ""
    status: str = "Pending_Review"
    confirmed_am_id: Optional[str] = None
    forensic_notes: Optional[str] = None

class ReconciliationReport(BaseModel):
    report_id: str = ""
    disaster_event: str = ""
    generated_at: str = ""
    coordinator_name: str = ""
    total_unidentified_bodies: int = 0
    total_missing_persons: int = 0
    reconciliations: List[BodyReconciliation] = []

class ConfirmationRequest(BaseModel):
    post_mortem_id: str
    ante_mortem_id: str
    forensic_officer: str
    confirmation_method: str
    notes: Optional[str] = None
