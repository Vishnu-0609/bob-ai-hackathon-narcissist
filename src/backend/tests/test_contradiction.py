import pytest
from app.services.contradiction_engine import ContradictionEngine
from app.models.entities import AMCase, PMCase


def test_sex_contradiction():
    am = AMCase(sex="MALE", age=30, height_cm=170.0, blood_group="O+")
    pm = PMCase(sex="FEMALE", estimated_age_min=28, estimated_age_max=32, height_cm=170.0, blood_group="O+")

    res = ContradictionEngine.detect_contradictions(am, pm)
    assert res["contradiction_status"] == "STRONG_CONTRADICTION"
    assert any(c["field"] == "sex" for c in res["contradictions"])


def test_blood_group_contradiction():
    am = AMCase(sex="MALE", age=30, height_cm=170.0, blood_group="O+")
    pm = PMCase(sex="MALE", estimated_age_min=28, estimated_age_max=32, height_cm=170.0, blood_group="AB-")

    res = ContradictionEngine.detect_contradictions(am, pm)
    assert res["contradiction_status"] == "STRONG_CONTRADICTION"
    assert any(c["field"] == "blood_group" for c in res["contradictions"])


def test_height_severe_discrepancy():
    am = AMCase(sex="MALE", age=30, height_cm=160.0, blood_group="O+")
    pm = PMCase(sex="MALE", estimated_age_min=28, estimated_age_max=32, height_cm=185.0, blood_group="O+")  # 25 cm diff

    res = ContradictionEngine.detect_contradictions(am, pm)
    assert res["contradiction_status"] in ("CONTRADICTION_REVIEW", "CONTRADICTION")
    assert any(c["field"] == "height" for c in res["contradictions"])


def test_missing_info_is_never_contradiction():
    am = AMCase(sex="MALE", age=None, height_cm=None, blood_group=None)
    pm = PMCase(sex="MALE", estimated_age_min=28, estimated_age_max=32, height_cm=175.0, blood_group="O+")

    res = ContradictionEngine.detect_contradictions(am, pm)
    assert res["contradiction_status"] == "NONE"
    assert len(res["contradictions"]) == 0
    assert "blood_group" in res["unknown_fields"]
    assert "height" in res["unknown_fields"]
