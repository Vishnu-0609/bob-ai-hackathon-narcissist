"""
End-to-End Test and Verification Script
Tests simplified post-mortem body workflow with multi-image intake,
visual feature extraction, and IBM Bob NLP natural language search.
"""
import io
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from app.main import app

def create_synthetic_image(color=(120, 80, 200), shape="rect") -> io.BytesIO:
    """Creates a synthetic image for test uploads."""
    img = Image.new("RGB", (200, 200), color=color)
    draw = ImageDraw.Draw(img)
    if shape == "circle":
        draw.ellipse([40, 40, 160, 160], fill=(240, 240, 240))
    else:
        draw.rectangle([40, 40, 160, 160], fill=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def run_tests():
    print("=" * 65)
    print(" Testing IBM Bob NLP Search & Multi-Image Feature Extraction")
    print("=" * 65)

    client = TestClient(app)

    # 1. Health Check
    print("\n1. Testing /api/health endpoint...")
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    health = resp.json()
    print(f"   Status: {health['status']}")
    print(f"   Total Bodies in Registry: {health['total_bodies']}")
    assert health['total_bodies'] >= 1

    # 2. Test Multi-Image Feature Extraction Endpoint
    print("\n2. Testing /api/extract-features with multiple images...")
    img1 = create_synthetic_image(color=(240, 240, 240)) # white
    img2 = create_synthetic_image(color=(30, 40, 160))   # blue
    files = [
        ("images", ("photo1.jpg", img1, "image/jpeg")),
        ("images", ("photo2.jpg", img2, "image/jpeg"))
    ]
    resp = client.post("/api/extract-features", files=files)
    assert resp.status_code == 200, f"Extract features failed: {resp.text}"
    extracted = resp.json()
    print(f"   Analyzed {extracted['total_images_analyzed']} images.")
    print(f"   Summary: {extracted.get('summary')}")
    assert extracted["total_images_analyzed"] == 2

    # 3. Upload Body with Multiple Images
    print("\n3. Testing body upload with multiple images (auto feature extraction)...")
    img_body1 = create_synthetic_image(color=(220, 20, 20)) # red/maroon
    img_body2 = create_synthetic_image(color=(50, 50, 50))  # dark/black
    files_upload = [
        ("images", ("garment.jpg", img_body1, "image/jpeg")),
        ("images", ("belongings.jpg", img_body2, "image/jpeg"))
    ]
    data = {
        "tag": "Body-NLP-01",
        "location": "Bilaspur Junction Platform 3",
        "gender": "Male",
        "age": "32",
        "details": "White cotton kurta, black leather wristwatch, surgical scar"
    }
    resp = client.post("/api/bodies", data=data, files=files_upload)
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    body_record = resp.json()
    body_id = body_record["id"]
    print(f"   Uploaded Body ID: {body_id} ({body_record['tag']})")
    assert len(body_record["image_paths"]) == 2
    assert body_record.get("extracted_features") is not None

    # 4. Test IBM Bob NLP Search Endpoint (/api/nlp-search)
    print("\n4. Testing /api/nlp-search with conversational query...")
    query = "find male body in bilaspur with white kurta and wristwatch"
    resp = client.get("/api/nlp-search", params={"q": query})
    assert resp.status_code == 200, f"NLP search failed: {resp.text}"
    nlp_res = resp.json()
    print(f"   Parsed Query Intent: {nlp_res['parsed_intent']['intent_summary']}")
    print(f"   Found {nlp_res['total_matches']} ranked matches.")
    assert nlp_res["total_matches"] >= 1
    top_match = nlp_res["results"][0]
    print(f"   Top Match: {top_match['body']['id']} ({top_match['body']['location']})")
    print(f"   NLP Score: {top_match['nlp_score']}%")
    print(f"   NLP Rationale: {top_match['nlp_rationale']}")
    assert top_match["body"]["id"] == body_id or "bilaspur" in top_match["body"]["location"].lower()
    print("   [PASS] IBM Bob NLP successfully identified matching body!")

    # 5. Test Bodies Endpoint with NLP Parameter (/api/bodies?q=...&nlp=true)
    print("\n5. Testing /api/bodies?q=...&nlp=true...")
    resp = client.get("/api/bodies", params={"q": "who was found at bilaspur wearing white?", "nlp": True})
    assert resp.status_code == 200
    bodies_nlp = resp.json()
    assert len(bodies_nlp) >= 1
    print(f"   Returned {len(bodies_nlp)} bodies with NLP scores:")
    for b in bodies_nlp[:2]:
        print(f"   - {b['id']} ({b['location']}): {b.get('nlp_score')}% -> {b.get('nlp_rationale')}")
    assert bodies_nlp[0].get("nlp_score") is not None
    print("   [PASS] /api/bodies returns calibrated Bob NLP match scores and rationales!")

    # 6. Test Gemini Status and Re-Extraction Endpoints
    print("\n6. Testing /api/config/gemini-status and /api/bodies/{body_id}/re-extract...")
    resp = client.get("/api/config/gemini-status")
    assert resp.status_code == 200, f"Gemini status failed: {resp.text}"
    status_data = resp.json()
    print(f"   Initial Gemini configured: {status_data['gemini_configured']}, Model: {status_data['model']}")

    # Test re-extracting features for the uploaded body
    resp = client.post(f"/api/bodies/{body_id}/re-extract")
    assert resp.status_code == 200, f"Re-extraction failed: {resp.text}"
    re_res = resp.json()
    assert re_res["status"] == "success"
    print(f"   Re-extracted features summary: {re_res['body']['extracted_features']['summary']}")
    print("   [PASS] Feature re-extraction succeeded!")

    # Test configuring Gemini key endpoint validation
    resp = client.post("/api/config/gemini-key", json={"api_key": "short"})
    assert resp.status_code == 400
    print("   [PASS] Short key correctly rejected with 400.")

    # 7. Clean up
    print(f"\n7. Cleaning up test body {body_id}...")
    resp = client.delete(f"/api/bodies/{body_id}")
    assert resp.status_code == 200
    print("   [PASS] Test body successfully deleted.")

    print("\n" + "=" * 65)
    print(" ALL IBM BOB NLP & GEMINI TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
