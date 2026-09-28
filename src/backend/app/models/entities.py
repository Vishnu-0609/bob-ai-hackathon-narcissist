import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    date = Column(DateTime, default=utc_now)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="ACTIVE")  # ACTIVE, ARCHIVED, CLOSED
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    am_cases = relationship("AMCase", back_populates="incident", cascade="all, delete-orphan")
    pm_cases = relationship("PMCase", back_populates="incident", cascade="all, delete-orphan")
    images = relationship("ImageEvidence", back_populates="incident", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="VIEWER")
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class AMCase(Base):
    __tablename__ = "am_cases"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=False, index=True)
    case_number = Column(String(100), nullable=False, index=True)  # e.g., AM-042
    name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=True)
    sex = Column(String(20), nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    blood_group = Column(String(10), nullable=True)
    physical_description = Column(Text, nullable=True)
    scars = Column(JSON, default=list)  # list of dicts: [{"location": ..., "description": ...}]
    birthmarks = Column(JSON, default=list)
    tattoos = Column(JSON, default=list)
    clothing = Column(JSON, default=list)  # list of strings/descriptions
    jewellery = Column(JSON, default=list)
    dental_notes = Column(Text, nullable=True)
    medical_history = Column(Text, nullable=True)
    implants = Column(JSON, default=list)
    last_seen_location = Column(String(255), nullable=True)
    last_seen_time = Column(String(100), nullable=True)
    source = Column(String(255), nullable=True)
    source_type = Column(String(50), default="FAMILY_INTERVIEW")  # FAMILY_INTERVIEW, MEDICAL_RECORD, etc.
    provenance_details = Column(JSON, default=dict)
    version = Column(Integer, default=1)
    created_by = Column(String(100), default="SYSTEM")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    incident = relationship("Incident", back_populates="am_cases")
    matches = relationship("Match", back_populates="am_case", cascade="all, delete-orphan")
    images = relationship("ImageEvidence", back_populates="am_case", cascade="all, delete-orphan", foreign_keys="[ImageEvidence.am_id]")


class PMCase(Base):
    __tablename__ = "pm_cases"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=False, index=True)
    body_number = Column(String(100), nullable=False, index=True)  # e.g., PM-017
    estimated_age_min = Column(Integer, nullable=True)
    estimated_age_max = Column(Integer, nullable=True)
    sex = Column(String(20), nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    blood_group = Column(String(10), nullable=True)
    physical_description = Column(Text, nullable=True)
    scars = Column(JSON, default=list)
    birthmarks = Column(JSON, default=list)
    tattoos = Column(JSON, default=list)
    clothing = Column(JSON, default=list)
    jewellery = Column(JSON, default=list)
    dental_findings = Column(Text, nullable=True)
    medical_findings = Column(Text, nullable=True)
    implants = Column(JSON, default=list)
    fingerprint_status = Column(String(50), default="NOT_AVAILABLE")  # AVAILABLE, PENDING, NOT_AVAILABLE
    dna_status = Column(String(50), default="NOT_AVAILABLE")
    recovery_location = Column(String(255), nullable=True)
    examiner = Column(String(255), nullable=True)
    provenance_details = Column(JSON, default=dict)
    version = Column(Integer, default=1)
    created_by = Column(String(100), default="SYSTEM")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    incident = relationship("Incident", back_populates="pm_cases")
    matches = relationship("Match", back_populates="pm_case", cascade="all, delete-orphan")
    images = relationship("ImageEvidence", back_populates="pm_case", cascade="all, delete-orphan", foreign_keys="[ImageEvidence.pm_id]")


class Match(Base):
    __tablename__ = "matches"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=False, index=True)
    pm_id = Column(String(64), ForeignKey("pm_cases.id"), nullable=False, index=True)
    am_id = Column(String(64), ForeignKey("am_cases.id"), nullable=False, index=True)
    match_score = Column(Float, nullable=False)  # 0 to 100
    evidence_quality = Column(String(50), default="MEDIUM")  # HIGH, MEDIUM, LOW, INSUFFICIENT
    data_completeness = Column(Float, default=0.0)  # 0 to 100
    contradiction_status = Column(String(50), default="NONE")  # NONE, CONTRADICTION_REVIEW, STRONG_CONTRADICTION
    candidate_rank = Column(Integer, default=1)  # 1, 2, 3
    status = Column(String(50), default="STRONG_CANDIDATE")
    # STRONG_CANDIDATE, MODERATE_CANDIDATE, INSUFFICIENT_EVIDENCE, CONTRADICTION_REVIEW, CONFIRMED_BY_FORENSIC_TEAM, REJECTED, NEEDS_REVIEW
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    pm_case = relationship("PMCase", back_populates="matches")
    am_case = relationship("AMCase", back_populates="matches")
    evidence_items = relationship("MatchEvidence", back_populates="match", cascade="all, delete-orphan")


class MatchEvidence(Base):
    __tablename__ = "match_evidence"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    match_id = Column(String(64), ForeignKey("matches.id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)  # sex, age, height, scars, etc.
    am_value = Column(Text, nullable=True)
    pm_value = Column(Text, nullable=True)
    comparison_result = Column(String(50), nullable=False)  # MATCH, MISMATCH, UNKNOWN, NOT_AVAILABLE
    weight = Column(Float, default=0.0)
    score_awarded = Column(Float, default=0.0)
    contradiction = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    provenance = Column(JSON, default=dict)

    match = relationship("Match", back_populates="evidence_items")


class MatchVersion(Base):
    __tablename__ = "match_versions"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    incident_id = Column(String(64), nullable=False, index=True)
    pm_id = Column(String(64), nullable=False, index=True)
    am_id = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    match_score = Column(Float, nullable=False)
    candidate_rank = Column(Integer, default=1)
    evidence_snapshot = Column(JSON, default=dict)
    algorithm_version = Column(String(50), default="1.0.0")
    weights_hash = Column(String(64), nullable=True)
    input_hash = Column(String(64), nullable=True)
    calculated_at = Column(DateTime, default=utc_now)


class Reconciliation(Base):
    __tablename__ = "reconciliations"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=False, index=True)
    pm_id = Column(String(64), ForeignKey("pm_cases.id"), nullable=False, index=True)
    am_id = Column(String(64), ForeignKey("am_cases.id"), nullable=False, index=True)
    decision = Column(String(50), nullable=False)
    # CONFIRMED_BY_FORENSIC_TEAM, REJECTED, NEEDS_REVIEW, PENDING_REVIEW
    reason = Column(Text, nullable=False)
    coordinator_comment = Column(Text, nullable=True)
    forensic_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(100), nullable=False)
    reviewed_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=False, index=True)
    pm_id = Column(String(64), nullable=False, index=True)
    am_id = Column(String(64), nullable=False, index=True)
    report_number = Column(String(100), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    content_json = Column(JSON, default=dict)
    pdf_path = Column(String(500), nullable=True)
    generated_by = Column(String(100), nullable=False)
    generated_at = Column(DateTime, default=utc_now)
    status = Column(String(50), default="DRAFT")  # DRAFT, FINAL, ARCHIVED


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    event_id = Column(String(100), unique=True, nullable=False, index=True)  # AUD-000123
    user_id = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)  # MATCH_CALCULATED, RECONCILIATION_CONFIRMED, etc.
    entity_type = Column(String(50), nullable=False)  # AM, PM, MATCH, RECONCILIATION, SYSTEM
    entity_id = Column(String(100), nullable=False)
    details = Column(JSON, default=dict)
    old_value_hash = Column(String(64), nullable=True)
    new_value_hash = Column(String(64), nullable=True)
    previous_event_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime, default=utc_now, index=True)


class BobInteraction(Base):
    __tablename__ = "bob_interactions"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    agent_name = Column(String(100), nullable=False)  # AM_EXTRACTION, PM_EXTRACTION, RATIONALE, EVIDENCE_GAP, COPILOT, REPORT
    request_id = Column(String(100), nullable=False, index=True)
    input_schema_hash = Column(String(64), nullable=True)
    output_schema_hash = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=utc_now)
    success = Column(Boolean, default=True)
    latency_ms = Column(Float, default=0.0)
    error_type = Column(String(100), nullable=True)


class ExtractionReview(Base):
    __tablename__ = "extraction_reviews"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    entity_type = Column(String(20), nullable=False)  # AM or PM
    raw_text = Column(Text, nullable=False)
    extracted_json = Column(JSON, default=dict)
    approved_json = Column(JSON, default=dict)
    status = Column(String(50), default="PENDING_REVIEW")  # PENDING_REVIEW, APPROVED, REJECTED, MODIFIED_AND_APPROVED
    extracted_by = Column(String(100), default="IBM_BOB")
    reviewed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    reviewed_at = Column(DateTime, nullable=True)


class ImageEvidence(Base):
    __tablename__ = "image_evidence"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=False, index=True)
    am_id = Column(String(64), ForeignKey("am_cases.id"), nullable=True, index=True)
    pm_id = Column(String(64), ForeignKey("pm_cases.id"), nullable=True, index=True)

    storage_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)

    image_type = Column(String(50), default="OTHER")
    # AM: PORTRAIT, FULL_BODY, CLOTHING, TATTOO, SCAR, JEWELLERY, OTHER
    # PM: BODY_OVERVIEW, CLOTHING, TATTOO, SCAR, JEWELLERY, INJURY, DENTAL, OTHER

    gemini_model = Column(String(100), default="gemini-2.5-flash")
    analysis_status = Column(String(50), default="PENDING")  # PENDING, ANALYZING, COMPLETED, FAILED
    extraction_json = Column(JSON, default=dict)

    human_review_status = Column(String(50), default="PENDING_REVIEW")  # PENDING_REVIEW, APPROVED, MODIFIED_AND_APPROVED, REJECTED
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    uploaded_by = Column(String(100), default="SYSTEM")
    uploaded_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    incident = relationship("Incident", back_populates="images")
    am_case = relationship("AMCase", back_populates="images", foreign_keys=[am_id])
    pm_case = relationship("PMCase", back_populates="images", foreign_keys=[pm_id])

