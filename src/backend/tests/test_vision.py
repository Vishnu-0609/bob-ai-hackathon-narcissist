import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.core.security import create_access_token
from app.models.entities import AMCase, PMCase, Incident, ImageEvidence
from app.services.vision.image_validator import ImageValidator, ImageValidationError
from app.services.vision.image_storage import ImageStorageService
from app.services.vision.gemini_client import (
    GeminiClient,
    GeminiVisionError,
    GeminiRateLimitError,
)
from app.services.vision.extraction_schema import ImageExtraction


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_access_token(
        data={"sub": "admin", "username": "admin", "role": "ADMIN"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_jpeg_bytes():
    buf = io.BytesIO()
    img = Image.new("RGB", (200, 200), color="blue")
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def sample_png_bytes():
    buf = io.BytesIO()
    img = Image.new("RGBA", (150, 150), color="green")
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_image_validator_valid_jpeg(sample_jpeg_bytes):
    res = ImageValidator.validate_image_bytes(
        file_bytes=sample_jpeg_bytes,
        filename="photo_test.jpg",
        declared_content_type="image/jpeg",
    )
    assert res["valid"] is True
    assert res["mime_type"] == "image/jpeg"
    assert res["width"] == 200
    assert res["height"] == 200
    assert len(res["sha256"]) == 64
    assert res["sanitized_filename"] == "photo_test.jpg"


def test_image_validator_rejects_empty():
    with pytest.raises(ImageValidationError, match="empty"):
        ImageValidator.validate_image_bytes(b"", "empty.jpg", "image/jpeg")


def test_image_validator_rejects_executable():
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00" + (b"\x00" * 100)
    with pytest.raises(ImageValidationError, match="Executable or script"):
        ImageValidator.validate_image_bytes(fake_exe, "payload.exe", "image/jpeg")


def test_image_validator_rejects_unsupported_mime():
    fake_pdf = b"%PDF-1.4\n" + (b"\x00" * 100)
    with pytest.raises(ImageValidationError, match="Unsupported image format"):
        ImageValidator.validate_image_bytes(fake_pdf, "document.pdf", "application/pdf")


def test_image_validator_rejects_oversized():
    huge_bytes = b"\xff\xd8\xff\xe0" + (b"\x00" * (11 * 1024 * 1024))
    with pytest.raises(ImageValidationError, match="exceeds maximum allowed"):
        ImageValidator.validate_image_bytes(huge_bytes, "huge.jpg", "image/jpeg")


def test_image_validator_sanitizes_path_traversal():
    clean = ImageValidator.sanitize_filename("../../../etc/passwd.jpg")
    assert ".." not in clean
    assert clean.endswith(".jpg")


def test_gemini_extraction_schema_validation():
    data = {
        "record_type": "AM",
        "image_type": "PORTRAIT",
        "observations": {
            "clothing": [
                {
                    "item_type": "shirt",
                    "color": "blue",
                    "description": "blue shirt",
                    "status": "OBSERVED",
                    "confidence": 0.95,
                }
            ],
            "jewellery": [
                {
                    "item_type": "ring",
                    "description": "silver ring",
                    "status": "OBSERVED",
                    "confidence": 0.88,
                }
            ],
            "tattoos": [
                {
                    "description": "bird tattoo",
                    "location": "right shoulder",
                    "status": "OBSERVED",
                    "confidence": 0.82,
                }
            ],
            "scars_or_marks": [
                {
                    "description": "3 cm scar",
                    "location": "left forearm",
                    "status": "OBSERVED",
                    "confidence": 0.75,
                }
            ],
            "physical_characteristics": [
                {
                    "attribute": "hair_color",
                    "value": "black",
                    "status": "OBSERVED",
                    "confidence": 0.90,
                },
                {
                    "attribute": "height",
                    "value": None,
                    "status": "UNKNOWN",
                    "confidence": 0.0,
                },
            ],
            "visible_text": [],
            "other_observations": [],
        },
        "image_quality": {
            "status": "GOOD",
            "occlusion": False,
        },
        "summary": "Clear portrait showing blue shirt and bird tattoo.",
    }

    validated = ImageExtraction.model_validate(data)
    assert validated.record_type == "AM"
    assert len(validated.observations.clothing) == 1
    assert validated.observations.clothing[0].color == "blue"
    # UNKNOWN handling
    unknown_char = next(
        p for p in validated.observations.physical_characteristics if p.attribute == "height"
    )
    assert unknown_char.status == "UNKNOWN"
    assert unknown_char.value is None


def test_gemini_client_mock_fallback(sample_jpeg_bytes):
    client = GeminiClient(api_key="")
    res = client.extract_image_evidence(sample_jpeg_bytes, "image/jpeg", record_type="AM")
    assert res["record_type"] == "AM"
    assert "observations" in res
    assert len(res["observations"]["clothing"]) > 0
    assert len(res["observations"]["tattoos"]) > 0


def test_image_upload_and_analyze_flow(test_client, auth_headers, sample_jpeg_bytes):
    # 1. Upload
    response = test_client.post(
        "/api/images/upload",
        headers=auth_headers,
        data={
            "incident_id": "INC-2023-BALASORE",
            "image_type": "PORTRAIT",
        },
        files={"file": ("test_photo.jpg", sample_jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 201
    img_data = response.json()
    image_id = img_data["id"]
    assert img_data["mime_type"] == "image/jpeg"
    assert img_data["analysis_status"] == "PENDING"
    assert img_data["human_review_status"] == "PENDING_REVIEW"

    # 2. Analyze (uses mock fallback when no real key is set)
    analyze_res = test_client.post(
        f"/api/images/{image_id}/analyze",
        headers=auth_headers,
    )
    assert analyze_res.status_code == 200
    res_json = analyze_res.json()
    assert res_json["analysis_status"] == "COMPLETED"
    assert "extracted_data" in res_json

    # 3. Retrieve analysis
    get_res = test_client.get(
        f"/api/images/{image_id}/analysis",
        headers=auth_headers,
    )
    assert get_res.status_code == 200
    record_json = get_res.json()
    assert record_json["id"] == image_id
    assert record_json["analysis_status"] == "COMPLETED"

    # 4. Fetch binary file
    file_res = test_client.get(
        f"/api/images/{image_id}/file",
        headers=auth_headers,
    )
    assert file_res.status_code == 200
    assert len(file_res.content) == len(sample_jpeg_bytes)


def test_human_review_and_am_sync(test_client, auth_headers, sample_jpeg_bytes):
    db = SessionLocal()
    try:
        am = db.query(AMCase).first()
        assert am is not None
        am_id = am.id
    finally:
        db.close()

    # 1. Upload for specific AM case
    up_res = test_client.post(
        "/api/images/upload",
        headers=auth_headers,
        data={
            "incident_id": "INC-2023-BALASORE",
            "am_id": am_id,
            "image_type": "TATTOO",
        },
        files={"file": ("tattoo_am.jpg", sample_jpeg_bytes, "image/jpeg")},
    )
    assert up_res.status_code == 201
    image_id = up_res.json()["id"]

    # 2. Analyze
    test_client.post(f"/api/images/{image_id}/analyze", headers=auth_headers)

    # 3. Human Review (Approved with modifications)
    approved_payload = {
        "decision": "MODIFIED_AND_APPROVED",
        "approved_observations": {
            "observations": {
                "clothing": [
                    {
                        "item_type": "shirt",
                        "color": "navy blue",
                        "description": "navy blue shirt",
                        "status": "OBSERVED",
                        "confidence": 0.98,
                    }
                ],
                "tattoos": [
                    {
                        "description": "eagle tattoo in flight",
                        "location": "right shoulder",
                        "status": "OBSERVED",
                        "confidence": 0.92,
                    }
                ],
                "scars_or_marks": [],
                "jewellery": [],
            },
            "summary": "Verified eagle tattoo and navy blue shirt by forensic coordinator.",
        },
        "notes": "Reviewed and confirmed with secondary family photograph.",
    }

    review_res = test_client.post(
        f"/api/images/{image_id}/review",
        headers=auth_headers,
        json=approved_payload,
    )
    assert review_res.status_code == 200
    rev_json = review_res.json()
    assert rev_json["human_review_status"] == "MODIFIED_AND_APPROVED"
    assert rev_json["reviewed_by"] == "admin"

    # 4. Verify evidence synced to AM Case
    db = SessionLocal()
    try:
        updated_am = db.query(AMCase).filter(AMCase.id == am_id).first()
        clothing_items = updated_am.clothing
        assert any("navy blue" in str(c) for c in clothing_items)
        tattoo_items = updated_am.tattoos
        assert any("eagle" in str(t) for t in tattoo_items)
    finally:
        db.close()


def test_human_rejection(test_client, auth_headers, sample_png_bytes):
    up_res = test_client.post(
        "/api/images/upload",
        headers=auth_headers,
        data={
            "incident_id": "INC-2023-BALASORE",
            "image_type": "OTHER",
        },
        files={"file": ("unclear_artifact.png", sample_png_bytes, "image/png")},
    )
    image_id = up_res.json()["id"]

    reject_payload = {
        "decision": "REJECTED",
        "approved_observations": {"observations": {}},
        "notes": "Image is severely degraded and does not show verifiable anatomical markings.",
    }

    rev_res = test_client.post(
        f"/api/images/{image_id}/review",
        headers=auth_headers,
        json=reject_payload,
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["human_review_status"] == "REJECTED"


def test_gemini_client_rate_limit_retry(sample_jpeg_bytes):
    from google.genai.errors import APIError

    mock_genai_client = MagicMock()
    # Simulate 429 then success
    error_429 = APIError(429, {"error": {"message": "Resource exhausted / rate limit"}})

    success_resp = MagicMock()
    success_resp.text = '{"record_type": "AM", "image_type": "CLOTHING", "observations": {"clothing": [{"description": "blue jacket", "status": "OBSERVED", "confidence": 0.9}]}, "image_quality": {"status": "GOOD", "occlusion": false}}'

    mock_genai_client.models.generate_content.side_effect = [error_429, success_resp]

    client = GeminiClient(api_key="test-key", max_retries=2)
    client._client = mock_genai_client

    result = client.extract_image_evidence(sample_jpeg_bytes, "image/jpeg", record_type="AM")
    assert result["record_type"] == "AM"
    assert mock_genai_client.models.generate_content.call_count == 2


def test_gemini_client_handles_unrecoverable_500(sample_jpeg_bytes):
    from google.genai.errors import APIError

    mock_genai_client = MagicMock()
    error_500 = APIError(500, {"error": {"message": "Google Internal Server Error"}})

    mock_genai_client.models.generate_content.side_effect = [error_500, error_500]

    client = GeminiClient(api_key="test-key", max_retries=2)
    client._client = mock_genai_client

    with pytest.raises(GeminiVisionError) as exc_info:
        client.extract_image_evidence(sample_jpeg_bytes, "image/jpeg", record_type="AM")

    assert exc_info.value.status_code == 500

