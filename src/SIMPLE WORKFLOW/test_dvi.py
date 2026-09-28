"""
Comprehensive End-to-End Test Suite for Bob DVI Coordinator
Simulates real-world Odisha Balasore train disaster reconciliation.
"""
import sys
from fastapi.testclient import TestClient
from app.main import app

def test_bob_dvi_system():
    print("=" * 70)
    print(" TESTING BOB DVI COORDINATOR (ODISHA BALASORE DISASTER SIMULATION)")
    print("=" * 70)

    with TestClient(app) as client:
        # 1. Health check & Initial State
        print("\n[1] Testing /api/health...")
        # Ensure seeded
        client.post("/api/seed-balasore")
        resp = client.get("/api/health")
        assert resp.status_code == 200, f"Health check failed: {resp.text}"
        health = resp.json()
        print(f"    System Status: {health['status']}")
        print(f"    CLIP Model: {health['clip_model']} on {health['device']}")
        print(f"    AM Missing Profiles: {health['total_ante_mortem_records']}")
        print(f"    PM Bodies Logged: {health['total_post_mortem_records']}")
        assert health['total_ante_mortem_records'] >= 3, "Balasore AM dataset should be seeded"
        assert health['total_post_mortem_records'] >= 3, "Balasore PM dataset should be seeded"

        # 2. Test Bob Cross-Referencing on Body PM-BAL-042 (Coach B4)
        print("\n[2] Testing Bob Cross-Referencing on PM-BAL-042 (Balasore Coach B4)...")
        resp = client.get("/api/cross-reference/PM-BAL-042")
        assert resp.status_code == 200, f"Cross-reference failed: {resp.text}"
        recon = resp.json()
        candidates = recon["top_candidates"]
        
        print(f"    Body ID: {recon['post_mortem_id']}")
        print(f"    Location: {recon['post_mortem_record']['recovery_location']}")
        print(f"    Candidates Surfaced by Bob: {len(candidates)}")
        assert len(candidates) == 3, f"Bob should surface top 3 candidates, got {len(candidates)}"

        top_match = candidates[0]
        print(f"\n    Rank #1 Candidate: {top_match['missing_person_name']} ({top_match['ante_mortem_id']})")
        print(f"    Match Probability: {top_match['match_probability']}%")
        print(f"    Semantic CLIP Similarity: {top_match['semantic_clip_similarity']}%")
        print(f"    Bob Rationale: {top_match['rationale']}")
        print("    Matching Factors:")
        for f in top_match['matching_factors']:
            print(f"      + {f}")

        assert top_match["ante_mortem_id"] == "AM-BAL-014", "Top candidate must be Subrata Sen (AM-BAL-014)!"
        assert top_match["match_probability"] >= 80.0, f"High confidence expected, got {top_match['match_probability']}%"
        print("    [PASS] Subrata Sen correctly identified as top match for Coach B4 body!")

        # 3. Test Bob Cross-Referencing on Body PM-BAL-109 (Coach S1)
        print("\n[3] Testing Bob Cross-Referencing on PM-BAL-109 (Balasore Coach S1)...")
        resp = client.get("/api/cross-reference/PM-BAL-109")
        assert resp.status_code == 200
        top_cand2 = resp.json()["top_candidates"][0]
        print(f"    Rank #1 Candidate: {top_cand2['missing_person_name']} ({top_cand2['ante_mortem_id']})")
        print(f"    Match Probability: {top_cand2['match_probability']}%")
        assert top_cand2["ante_mortem_id"] == "AM-BAL-055", "Top candidate must be Priya Sharma (AM-BAL-055)!"
        print("    [PASS] Priya Sharma correctly identified as top match for Coach S1 body!")

        # 4. Test Bob Cross-Referencing on Body PM-BAL-187 (Track Km 254)
        print("\n[4] Testing Bob Cross-Referencing on PM-BAL-187 (Track Km 254)...")
        resp = client.get("/api/cross-reference/PM-BAL-187")
        assert resp.status_code == 200
        top_cand3 = resp.json()["top_candidates"][0]
        print(f"    Rank #1 Candidate: {top_cand3['missing_person_name']} ({top_cand3['ante_mortem_id']})")
        print(f"    Match Probability: {top_cand3['match_probability']}%")
        assert top_cand3["ante_mortem_id"] == "AM-BAL-089", "Top candidate must be Rajesh Soren (AM-BAL-089)!"
        print("    [PASS] Rajesh Soren correctly identified as top match for Track Km 254 body!")

        # 5. Test Forensic Confirmation Execution
        print("\n[5] Testing Forensic Confirmation Execution...")
        confirm_payload = {
            "post_mortem_id": "PM-BAL-042",
            "ante_mortem_id": "AM-BAL-014",
            "forensic_officer": "Dr. R. K. Mohapatra (Head of Forensic Medicine, AIIMS Bhubaneswar)",
            "confirmation_method": "Distinctive Biomarker Concordance (Appendectomy scar + dental crown + blue sapphire ring)",
            "notes": "Verified against WB Aadhaar biometric records; Executive Magistrate Balasore notified for family release."
        }
        resp = client.post("/api/confirm-reconciliation", json=confirm_payload)
        assert resp.status_code == 200, f"Confirmation failed: {resp.text}"
        print(f"    Confirmation Result: {resp.json()['message']}")

        # Verify updated status
        resp_updated = client.get("/api/cross-reference/PM-BAL-042")
        assert resp_updated.json()["status"] == "Confirmed", "Status should be Confirmed"
        print("    [PASS] Status updated to Confirmed in reconciliation registry.")

        # 6. Test DVI Reconciliation Report Generation
        print("\n[6] Testing Reconciliation Report Generation (JSON & Printable HTML)...")
        resp_rep = client.get("/api/reconciliation-report")
        assert resp_rep.status_code == 200
        rep = resp_rep.json()
        print(f"    Generated Report ID: {rep['report_id']}")
        print(f"    Disaster Incident: {rep['disaster_event']}")
        print(f"    Reconciled Case Entries: {len(rep['reconciliations'])}")

        resp_html = client.get("/api/reconciliation-report/print")
        assert resp_html.status_code == 200
        assert "DISASTER VICTIM IDENTIFICATION (DVI) RECONCILIATION REPORT" in resp_html.text
        assert "Subrata Sen" in resp_html.text
        print("    [PASS] Printable DVI Reconciliation Report rendered successfully.")

    print("\n" + "=" * 70)
    print(" ALL 6 BOB DVI TESTS COMPLETED & VERIFIED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_bob_dvi_system()
