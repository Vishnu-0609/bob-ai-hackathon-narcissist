import os
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash, UserRole
from app.models.entities import User, Incident, AMCase, PMCase, Match, Reconciliation
from app.services.audit_service import AuditService
from app.services.candidate_service import CandidateService


def seed_database(db: Session):
    # 1. Seed Users
    default_users = [
        {"username": "admin", "email": "admin@dvi-bridge.org", "password": "adminpassword123", "role": UserRole.ADMIN, "full_name": "Dr. Rajesh Varma (Admin)"},
        {"username": "coordinator", "email": "coordinator@dvi-bridge.org", "password": "coordpassword123", "role": UserRole.DVI_COORDINATOR, "full_name": "Sarah Jenkins (Lead DVI Coordinator)"},
        {"username": "reviewer", "email": "forensic@dvi-bridge.org", "password": "reviewpassword123", "role": UserRole.FORENSIC_REVIEWER, "full_name": "Dr. Aris Thorne (Chief Pathologist)"},
        {"username": "field_team", "email": "field@dvi-bridge.org", "password": "fieldpassword123", "role": UserRole.FIELD_OPERATOR, "full_name": "NDRF Field Unit 4"},
        {"username": "auditor", "email": "auditor@dvi-bridge.org", "password": "auditpassword123", "role": UserRole.AUDITOR, "full_name": "Meera Patel (Oversight Auditor)"},
    ]

    for u in default_users:
        existing = db.query(User).filter(User.username == u["username"]).first()
        if not existing:
            new_u = User(
                username=u["username"],
                email=u["email"],
                hashed_password=get_password_hash(u["password"]),
                role=u["role"],
                full_name=u["full_name"],
                is_active=True,
            )
            db.add(new_u)
    db.commit()

    # 2. Seed Incident
    inc_id = "INC-2023-BALASORE"
    inc = db.query(Incident).filter(Incident.id == inc_id).first()
    if not inc:
        inc = Incident(
            id=inc_id,
            name="Odisha Train Collision — DVI Operations",
            location="Bahanaga Bazar Station, Balasore District, Odisha",
            date=datetime(2023, 6, 2, 19, 0, 0, tzinfo=timezone.utc),
            description="Mass-casualty triple train collision response requiring high-throughput ante-mortem and post-mortem reconciliation across multiple district morgues.",
            status="ACTIVE",
        )
        db.add(inc)
        db.commit()
        db.refresh(inc)

        AuditService.log_event(
            db=db,
            user_id="admin",
            role=UserRole.ADMIN,
            action="INCIDENT_INITIALIZED",
            entity_type="INCIDENT",
            entity_id=inc.id,
            details={"name": inc.name, "location": inc.location},
        )

    # 3. Optional Synthetic AM and PM seeding (only if SEED_SYNTHETIC_DATA is explicitly enabled)
    seed_synthetic = os.getenv("SEED_SYNTHETIC_DATA", "false").lower() in ("true", "1", "yes")
    existing_am_count = db.query(AMCase).filter(AMCase.incident_id == inc.id).count()
    if seed_synthetic and existing_am_count == 0:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        am_file = os.path.join(data_dir, "synthetic_am.json")
        pm_file = os.path.join(data_dir, "synthetic_pm.json")

        if os.path.exists(am_file) and os.path.exists(pm_file):
            try:
                with open(am_file, "r", encoding="utf-8") as f:
                    am_list = json.load(f)
                with open(pm_file, "r", encoding="utf-8") as f:
                    pm_list = json.load(f)

                for item in am_list:
                    am_obj = AMCase(
                        incident_id=inc.id,
                        case_number=item["case_number"],
                        name=item["name"],
                        age=item.get("age"),
                        sex=item.get("sex"),
                        height_cm=item.get("height_cm"),
                        weight_kg=item.get("weight_kg"),
                        blood_group=item.get("blood_group"),
                        physical_description=item.get("physical_description", ""),
                        scars=item.get("scars", []),
                        birthmarks=item.get("birthmarks", []),
                        tattoos=item.get("tattoos", []),
                        clothing=item.get("clothing", []),
                        jewellery=item.get("jewellery", []),
                        dental_notes=item.get("dental_notes"),
                        medical_history=item.get("medical_history"),
                        implants=item.get("implants", []),
                        last_seen_location=item.get("last_seen_location"),
                        last_seen_time=item.get("last_seen_time"),
                        source=item.get("source", "Family Intake Interview"),
                        source_type="FAMILY_INTERVIEW",
                        provenance_details={"captured_by": "Family Intake Team", "extracted_by": "IBM_BOB", "review_status": "HUMAN_VERIFIED"},
                        version=1,
                        created_by="SYSTEM",
                    )
                    db.add(am_obj)

                for item in pm_list:
                    pm_obj = PMCase(
                        incident_id=inc.id,
                        body_number=item["body_number"],
                        estimated_age_min=item.get("estimated_age_min"),
                        estimated_age_max=item.get("estimated_age_max"),
                        sex=item.get("sex"),
                        height_cm=item.get("height_cm"),
                        weight_kg=item.get("weight_kg"),
                        blood_group=item.get("blood_group"),
                        physical_description=item.get("physical_description", ""),
                        scars=item.get("scars", []),
                        birthmarks=item.get("birthmarks", []),
                        tattoos=item.get("tattoos", []),
                        clothing=item.get("clothing", []),
                        jewellery=item.get("jewellery", []),
                        dental_findings=item.get("dental_findings"),
                        medical_findings=item.get("medical_findings"),
                        implants=item.get("implants", []),
                        fingerprint_status=item.get("fingerprint_status", "NOT_AVAILABLE"),
                        dna_status=item.get("dna_status", "NOT_AVAILABLE"),
                        recovery_location=item.get("recovery_location"),
                        examiner=item.get("examiner", "Dr. A. Thorne"),
                        provenance_details={"source_type": "MORTUARY_OBSERVATION", "extracted_by": "IBM_BOB", "review_status": "HUMAN_VERIFIED"},
                        version=1,
                        created_by="SYSTEM",
                    )
                    db.add(pm_obj)

                db.commit()
                print(f"[Seed] Successfully loaded {len(am_list)} AM cases and {len(pm_list)} PM cases.")
            except Exception as e:
                print(f"[Seed] Error reading synthetic files: {e}")


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
