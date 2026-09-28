import pytest
from app.services.matching_engine import MatchingEngine
from app.models.entities import AMCase, PMCase


def test_exact_match_score():
    engine = MatchingEngine()
    am = AMCase(
        case_number="AM-001",
        name="John Doe",
        age=34,
        sex="MALE",
        height_cm=173.0,
        blood_group="O+",
        scars=[{"location": "left forearm", "description": "3 cm scar"}],
        birthmarks=[{"location": "left cheek", "description": "mole"}],
        tattoos=[{"location": "right shoulder", "description": "bird"}],
        clothing=["blue shirt", "dark jeans"],
        jewellery=["silver ring"],
        dental_notes="Dental crowding lower anterior",
        medical_history="Left forearm fracture healed",
        last_seen_location="Coach B-3",
    )
    pm = PMCase(
        body_number="PM-001",
        estimated_age_min=32,
        estimated_age_max=36,
        sex="MALE",
        height_cm=173.0,
        blood_group="O+",
        scars=[{"location": "left forearm", "description": "3 cm scar"}],
        birthmarks=[{"location": "left cheek", "description": "mole"}],
        tattoos=[{"location": "right shoulder", "description": "bird"}],
        clothing=["blue shirt", "dark jeans"],
        jewellery=["silver ring"],
        dental_findings="Dental crowding lower anterior",
        medical_findings="Left forearm fracture healed",
        recovery_location="Coach B-3",
    )

    res = engine.evaluate_pair(pm, am)
    assert res["match_score"] == 100.0
    assert res["contradiction_status"] == "NONE"
    assert res["status"] == "STRONG_CANDIDATE"
    assert len(res["supporting_evidence"]) == 12


def test_missing_data_not_treated_as_mismatch():
    engine = MatchingEngine()
    am = AMCase(
        case_number="AM-002",
        name="Jane Doe",
        age=28,
        sex="FEMALE",
        height_cm=165.0,
        blood_group=None,  # Missing
        scars=[],  # None recorded
        birthmarks=[],
        tattoos=[],
        clothing=[],
        jewellery=[],
        dental_notes=None,
        medical_history=None,
        last_seen_location="Sector A",
    )
    pm = PMCase(
        body_number="PM-002",
        estimated_age_min=26,
        estimated_age_max=30,
        sex="FEMALE",
        height_cm=165.0,
        blood_group="A+",  # Present in PM
        scars=[],
        birthmarks=[],
        tattoos=[],
        clothing=[],
        jewellery=[],
        dental_findings=None,
        medical_findings=None,
        recovery_location="Sector A",
    )

    res = engine.evaluate_pair(pm, am)
    # Blood group missing in AM must be UNKNOWN, not MISMATCH or contradiction
    bg_evidence = next(e for e in res["evidence_items"] if e["field_name"] == "blood_group")
    assert bg_evidence["comparison_result"] == "UNKNOWN"
    assert bg_evidence["contradiction"] is False
    assert res["contradiction_status"] == "NONE"
