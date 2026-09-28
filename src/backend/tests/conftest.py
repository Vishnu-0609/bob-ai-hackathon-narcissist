import pytest
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash, UserRole
from app.models.entities import User, Incident, AMCase, PMCase


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Ensure test users
        users = [
            {"username": "admin", "email": "admin@dvi-bridge.org", "password": "adminpassword123", "role": UserRole.ADMIN, "full_name": "Dr. Rajesh Varma"},
            {"username": "coordinator", "email": "coordinator@dvi-bridge.org", "password": "coordpassword123", "role": UserRole.DVI_COORDINATOR, "full_name": "Sarah Jenkins"},
        ]
        for u in users:
            existing = db.query(User).filter(User.username == u["username"]).first()
            if not existing:
                db.add(User(
                    username=u["username"],
                    email=u["email"],
                    hashed_password=get_password_hash(u["password"]),
                    role=u["role"],
                    full_name=u["full_name"],
                    is_active=True,
                ))

        # 2. Ensure test incident
        inc_id = "INC-2023-BALASORE"
        inc = db.query(Incident).filter(Incident.id == inc_id).first()
        if not inc:
            inc = Incident(
                id=inc_id,
                name="Odisha Train Collision — DVI Operations",
                location="Bahanaga Bazar Station, Balasore District, Odisha",
                status="ACTIVE",
            )
            db.add(inc)
            db.commit()

        # 3. Ensure test AM cases for unit test evaluation
        test_am_cases = [
            {
                "case_number": "AM-042",
                "name": "Arjun Mohanty",
                "age": 34,
                "sex": "MALE",
                "height_cm": 173.0,
                "weight_kg": 68.0,
                "blood_group": "O+",
                "physical_description": "Medium build, short dark hair, reported traveling in Coach B-3.",
                "scars": [{"location": "left forearm", "description": "3 cm healed linear scar"}],
                "birthmarks": [{"location": "left cheek", "description": "small dark mole"}],
                "tattoos": [{"location": "right shoulder", "description": "bird in flight"}],
                "clothing": ["blue shirt", "dark blue jeans"],
                "jewellery": ["silver ring on right ring finger"],
                "dental_notes": "Mild crowding in lower anterior teeth, dental chart available upon request",
                "medical_history": "Healed left forearm fracture from 2018",
                "last_seen_location": "Coromandel Express Coach B-3",
                "last_seen_time": "2023-06-02 18:45",
            },
            {
                "case_number": "AM-001",
                "name": "Test Subject One",
                "age": 28,
                "sex": "MALE",
                "height_cm": 170.0,
                "blood_group": "A+",
                "physical_description": "28-year-old male.",
                "scars": [],
                "tattoos": [],
                "clothing": ["red t-shirt"],
                "jewellery": [],
            },
            {
                "case_number": "AM-002",
                "name": "Test Subject Two",
                "age": 45,
                "sex": "FEMALE",
                "height_cm": 160.0,
                "blood_group": "B+",
                "physical_description": "45-year-old female.",
                "scars": [],
                "tattoos": [],
                "clothing": ["yellow saree"],
                "jewellery": [],
            },
        ]
        for am_data in test_am_cases:
            existing_am = db.query(AMCase).filter(AMCase.case_number == am_data["case_number"]).first()
            if existing_am:
                for k, v in am_data.items():
                    setattr(existing_am, k, v)
            else:
                db.add(AMCase(
                    incident_id=inc_id,
                    case_number=am_data["case_number"],
                    name=am_data["name"],
                    age=am_data["age"],
                    sex=am_data["sex"],
                    height_cm=am_data["height_cm"],
                    weight_kg=am_data.get("weight_kg"),
                    blood_group=am_data["blood_group"],
                    physical_description=am_data["physical_description"],
                    scars=am_data["scars"],
                    birthmarks=am_data.get("birthmarks", []),
                    tattoos=am_data["tattoos"],
                    clothing=am_data["clothing"],
                    jewellery=am_data["jewellery"],
                    dental_notes=am_data.get("dental_notes"),
                    medical_history=am_data.get("medical_history"),
                    last_seen_location=am_data.get("last_seen_location"),
                    version=1,
                    created_by="TEST_FIXTURE",
                ))

        # 4. Ensure test PM cases for unit test evaluation
        test_pm_cases = [
            {
                "body_number": "PM-017",
                "estimated_age_min": 32,
                "estimated_age_max": 36,
                "sex": "MALE",
                "height_cm": 172.0,
                "weight_kg": 67.0,
                "blood_group": "O+",
                "physical_description": "Male body, medium build, intact friction ridges on digits.",
                "scars": [{"location": "left forearm", "description": "healed linear surgical scar approx 3 cm"}],
                "birthmarks": [{"location": "left cheek", "description": "small dark mole"}],
                "tattoos": [{"location": "right shoulder", "description": "bird tattoo"}],
                "clothing": ["blue shirt", "dark jeans"],
                "jewellery": ["silver ring on right hand"],
                "medical_findings": "Evidence of healed radius/ulna consolidation",
                "recovery_location": "Coromandel Express Coach B-3",
            },
        ]
        for pm_data in test_pm_cases:
            existing_pm = db.query(PMCase).filter(PMCase.body_number == pm_data["body_number"]).first()
            if existing_pm:
                for k, v in pm_data.items():
                    setattr(existing_pm, k, v)
            else:
                db.add(PMCase(
                    incident_id=inc_id,
                    body_number=pm_data["body_number"],
                    estimated_age_min=pm_data["estimated_age_min"],
                    estimated_age_max=pm_data["estimated_age_max"],
                    sex=pm_data["sex"],
                    height_cm=pm_data["height_cm"],
                    weight_kg=pm_data.get("weight_kg"),
                    blood_group=pm_data["blood_group"],
                    physical_description=pm_data["physical_description"],
                    scars=pm_data["scars"],
                    birthmarks=pm_data.get("birthmarks", []),
                    tattoos=pm_data["tattoos"],
                    clothing=pm_data["clothing"],
                    jewellery=pm_data["jewellery"],
                    medical_findings=pm_data.get("medical_findings"),
                    recovery_location=pm_data["recovery_location"],
                    version=1,
                    created_by="TEST_FIXTURE",
                ))

        db.commit()
    finally:
        db.close()

    yield

    # Teardown: Clean test cases to leave production database pristine
    db = SessionLocal()
    try:
        from app.models.entities import MatchEvidence, MatchVersion, Match, Reconciliation, Report, ExtractionReview, BobInteraction, ImageEvidence
        db.query(Reconciliation).delete()
        db.query(Report).delete()
        db.query(MatchEvidence).delete()
        db.query(MatchVersion).delete()
        db.query(Match).delete()
        db.query(ImageEvidence).delete()
        db.query(ExtractionReview).delete()
        db.query(BobInteraction).delete()
        db.query(AMCase).delete()
        db.query(PMCase).delete()
        db.commit()
    finally:
        db.close()
