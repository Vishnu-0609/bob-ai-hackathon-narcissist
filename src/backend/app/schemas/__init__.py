from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ==================== Auth & User Schemas ====================
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str
    full_name: str


class UserBase(BaseModel):
    username: str
    email: str
    role: str = "VIEWER"
    full_name: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Incident Schemas ====================
class IncidentBase(BaseModel):
    name: str
    location: str
    description: Optional[str] = None
    status: str = "ACTIVE"


class IncidentCreate(IncidentBase):
    date: Optional[datetime] = None


class IncidentResponse(IncidentBase):
    id: str
    date: datetime
    created_at: datetime
    updated_at: datetime
    am_count: Optional[int] = 0
    pm_count: Optional[int] = 0
    matched_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


# ==================== AM (Ante-Mortem) Schemas ====================
class FeatureItem(BaseModel):
    location: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None


class AMCaseBase(BaseModel):
    case_number: str
    name: str
    age: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_group: Optional[str] = None
    physical_description: Optional[str] = None
    scars: List[Any] = Field(default_factory=list)
    birthmarks: List[Any] = Field(default_factory=list)
    tattoos: List[Any] = Field(default_factory=list)
    clothing: List[Any] = Field(default_factory=list)
    jewellery: List[Any] = Field(default_factory=list)
    dental_notes: Optional[str] = None
    medical_history: Optional[str] = None
    implants: List[Any] = Field(default_factory=list)
    last_seen_location: Optional[str] = None
    last_seen_time: Optional[str] = None
    source: Optional[str] = None
    source_type: Optional[str] = "FAMILY_INTERVIEW"
    provenance_details: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AMCaseCreate(AMCaseBase):
    incident_id: str


class AMCaseUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_group: Optional[str] = None
    physical_description: Optional[str] = None
    scars: Optional[List[Any]] = None
    birthmarks: Optional[List[Any]] = None
    tattoos: Optional[List[Any]] = None
    clothing: Optional[List[Any]] = None
    jewellery: Optional[List[Any]] = None
    dental_notes: Optional[str] = None
    medical_history: Optional[str] = None
    implants: Optional[List[Any]] = None
    last_seen_location: Optional[str] = None
    last_seen_time: Optional[str] = None
    source: Optional[str] = None
    source_type: Optional[str] = None


class AMCaseResponse(AMCaseBase):
    id: str
    incident_id: str
    version: int
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== PM (Post-Mortem) Schemas ====================
class PMCaseBase(BaseModel):
    body_number: str
    estimated_age_min: Optional[int] = None
    estimated_age_max: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_group: Optional[str] = None
    physical_description: Optional[str] = None
    scars: List[Any] = Field(default_factory=list)
    birthmarks: List[Any] = Field(default_factory=list)
    tattoos: List[Any] = Field(default_factory=list)
    clothing: List[Any] = Field(default_factory=list)
    jewellery: List[Any] = Field(default_factory=list)
    dental_findings: Optional[str] = None
    medical_findings: Optional[str] = None
    implants: List[Any] = Field(default_factory=list)
    fingerprint_status: Optional[str] = "NOT_AVAILABLE"
    dna_status: Optional[str] = "NOT_AVAILABLE"
    recovery_location: Optional[str] = None
    examiner: Optional[str] = None
    provenance_details: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PMCaseCreate(PMCaseBase):
    incident_id: str


class PMCaseUpdate(BaseModel):
    estimated_age_min: Optional[int] = None
    estimated_age_max: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_group: Optional[str] = None
    physical_description: Optional[str] = None
    scars: Optional[List[Any]] = None
    birthmarks: Optional[List[Any]] = None
    tattoos: Optional[List[Any]] = None
    clothing: Optional[List[Any]] = None
    jewellery: Optional[List[Any]] = None
    dental_findings: Optional[str] = None
    medical_findings: Optional[str] = None
    implants: Optional[List[Any]] = None
    fingerprint_status: Optional[str] = None
    dna_status: Optional[str] = None
    recovery_location: Optional[str] = None
    examiner: Optional[str] = None


class PMCaseResponse(PMCaseBase):
    id: str
    incident_id: str
    version: int
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Extraction Schemas ====================
class ExtractionRequest(BaseModel):
    text: str
    incident_id: str
    source_type: Optional[str] = "FIELD_OBSERVATION"
    audio_present: Optional[bool] = False


class AMExtractionOutput(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_group: Optional[str] = None
    physical_description: Optional[str] = None
    scars: List[Dict[str, Any]] = Field(default_factory=list)
    birthmarks: List[Dict[str, Any]] = Field(default_factory=list)
    tattoos: List[Dict[str, Any]] = Field(default_factory=list)
    clothing: List[str] = Field(default_factory=list)
    jewellery: List[str] = Field(default_factory=list)
    dental_notes: Optional[str] = None
    medical_history: Optional[str] = None
    implants: List[str] = Field(default_factory=list)
    last_seen_location: Optional[str] = None
    last_seen_time: Optional[str] = None


class PMExtractionOutput(BaseModel):
    estimated_age_min: Optional[int] = None
    estimated_age_max: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_group: Optional[str] = None
    physical_description: Optional[str] = None
    scars: List[Dict[str, Any]] = Field(default_factory=list)
    birthmarks: List[Dict[str, Any]] = Field(default_factory=list)
    tattoos: List[Dict[str, Any]] = Field(default_factory=list)
    clothing: List[str] = Field(default_factory=list)
    jewellery: List[str] = Field(default_factory=list)
    dental_findings: Optional[str] = None
    medical_findings: Optional[str] = None
    implants: List[str] = Field(default_factory=list)
    recovery_location: Optional[str] = None
    examiner: Optional[str] = None


class ExtractionReviewSubmission(BaseModel):
    review_id: Optional[str] = None
    entity_type: str  # AM or PM
    incident_id: str
    case_identifier: str  # case_number or body_number
    approved_data: Dict[str, Any]
    decision: str = "APPROVED"  # APPROVED, REJECTED, MODIFIED_AND_APPROVED
    notes: Optional[str] = None


# ==================== Matching & Evidence Schemas ====================
class MatchEvidenceItem(BaseModel):
    field_name: str
    am_value: Optional[str] = None
    pm_value: Optional[str] = None
    comparison_result: str  # MATCH, MISMATCH, UNKNOWN, NOT_AVAILABLE
    weight: float
    score_awarded: float
    contradiction: bool = False
    notes: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CandidateMatch(BaseModel):
    match_id: Optional[str] = None
    am_id: str
    am_case_number: str
    am_name: str
    match_score: float
    evidence_quality: str
    data_completeness: float
    contradiction_status: str
    candidate_rank: int
    status: str
    supporting_evidence: List[MatchEvidenceItem] = Field(default_factory=list)
    contradictions: List[MatchEvidenceItem] = Field(default_factory=list)
    unknown: List[MatchEvidenceItem] = Field(default_factory=list)
    bob_rationale: Optional[str] = None
    evidence_gaps: Optional[Dict[str, Any]] = None
    reconciliation_status: Optional[str] = "PENDING_REVIEW"


class TopCandidatesResponse(BaseModel):
    pm_id: str
    pm_body_number: str
    candidates: List[CandidateMatch]
    total_candidates_evaluated: int
    calculation_timestamp: datetime


# ==================== Reconciliation Schemas ====================
class ReconciliationDecisionRequest(BaseModel):
    pm_id: str
    am_id: str
    decision: str  # CONFIRMED_BY_FORENSIC_TEAM, REJECTED, NEEDS_REVIEW, PENDING_REVIEW
    reason: str
    coordinator_comment: Optional[str] = None
    forensic_notes: Optional[str] = None


class ReconciliationResponse(BaseModel):
    id: str
    incident_id: str
    pm_id: str
    am_id: str
    decision: str
    reason: str
    coordinator_comment: Optional[str]
    forensic_notes: Optional[str]
    reviewed_by: str
    reviewed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Copilot & Chat Schemas ====================
class CopilotChatRequest(BaseModel):
    incident_id: str
    query: str
    context_pm_id: Optional[str] = None
    context_am_id: Optional[str] = None


class CopilotToolExecution(BaseModel):
    tool: str
    parameters: Dict[str, Any]
    result: Any


class CopilotChatResponse(BaseModel):
    response: str
    tools_used: List[CopilotToolExecution] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)
    intent: Optional[str] = None


# ==================== Report Schemas ====================
class ReportCreateRequest(BaseModel):
    incident_id: str
    pm_id: str
    am_id: str
    title: Optional[str] = None


class ReportResponse(BaseModel):
    id: str
    report_number: str
    incident_id: str
    pm_id: str
    am_id: str
    title: str
    summary: Optional[str] = None
    pdf_url: Optional[str] = None
    content_json: Dict[str, Any]
    generated_by: str
    generated_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


# ==================== Audit Schemas ====================
class AuditLogItem(BaseModel):
    id: str
    event_id: str
    user_id: str
    role: str
    action: str
    entity_type: str
    entity_id: str
    details: Dict[str, Any]
    old_value_hash: Optional[str]
    new_value_hash: Optional[str]
    previous_event_hash: str
    event_hash: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditVerifyResponse(BaseModel):
    valid: bool
    events_checked: int
    broken_at: Optional[str] = None
    last_event_hash: Optional[str] = None
    verification_time_ms: float


# ==================== Evaluation Schemas ====================
class EvaluationMetricsResponse(BaseModel):
    top1_accuracy: float
    top3_recall: float
    contradiction_detection_accuracy: float
    missing_data_robustness: float
    duplicate_detection_accuracy: float
    average_matching_latency_ms: float
    bob_extraction_validation_rate: float
    total_eval_cases: int
    ground_truth_matches: int
    exact_match_cases: int
    partial_match_cases: int
    contradiction_cases: int
    missing_data_cases: int
    duplicate_am_cases: int
    unmatched_cases: int
