from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.services.bob_client import bob_client


class BobRationaleService:
    @staticmethod
    def _generate_local_rationale(candidate_data: Dict[str, Any]) -> str:
        """
        Deterministic rationale builder strictly bound to the supplied comparison facts.
        """
        am_num = candidate_data.get("am_case_number", "AM Candidate")
        am_name = candidate_data.get("am_name", "")
        pm_num = candidate_data.get("pm_body_number", "PM Case")
        score = candidate_data.get("match_score", 0)
        quality = candidate_data.get("evidence_quality", "MEDIUM")

        supporting = candidate_data.get("supporting_evidence", [])
        contradictions = candidate_data.get("contradictions", [])
        unknown = candidate_data.get("unknown", [])

        matched_fields = [item.get("field_name") for item in supporting if item.get("field_name")]
        contradicted_fields = [item.get("field_name") for item in contradictions if item.get("field_name")]
        unknown_fields = [item.get("field_name") for item in unknown if item.get("field_name")]

        paragraphs = []

        # Intro
        target_name = f" ({am_name})" if am_name and am_name != "Unknown" else ""
        paragraphs.append(
            f"Candidate profile {am_num}{target_name} is ranked with a deterministic match score of {score}/100 "
            f"(Evidence Quality: {quality}) for post-mortem record {pm_num}."
        )

        # Supporting Evidence
        if matched_fields:
            evidence_summary = []
            for item in supporting:
                f_name = item.get("field_name", "")
                am_val = item.get("am_value", "")
                pm_val = item.get("pm_value", "")
                if f_name == "scars":
                    evidence_summary.append(f"anatomical scar correlation ({am_val})")
                elif f_name == "tattoos":
                    evidence_summary.append(f"matching tattoo features ({am_val})")
                elif f_name == "dental":
                    evidence_summary.append(f"concordant odontological findings ({am_val})")
                elif f_name in ("sex", "blood_group"):
                    evidence_summary.append(f"congruent {f_name.replace('_', ' ')} ({am_val})")
                elif f_name in ("age", "height"):
                    evidence_summary.append(f"compatible stature/age ({am_val} vs {pm_val})")
                elif f_name == "clothing":
                    evidence_summary.append(f"matching recovered clothing ({am_val})")
                else:
                    evidence_summary.append(f"aligned {f_name.replace('_', ' ')}")

            paragraphs.append(
                "Primary supporting evidence includes: " + "; ".join(evidence_summary) + "."
            )

        # Contradictions
        if contradicted_fields:
            contra_notes = [f"{item.get('field_name')}: {item.get('notes')}" for item in contradictions if item.get("notes")]
            paragraphs.append(
                "CRITICAL CONTRADICTIONS NOTED: " + "; ".join(contra_notes) + ". "
                "This discrepancy must be resolved prior to reconciliation."
            )
        else:
            paragraphs.append("No direct anatomical or serological contradictions were detected.")

        # Missing Evidence
        if unknown_fields:
            missing_names = [f.replace("_", " ") for f in unknown_fields[:5]]
            paragraphs.append(
                f"Missing or unobserved fields in one or both records include: {', '.join(missing_names)}. "
                "The match is non-conclusive until secondary forensic confirmation (such as comparative dental, DNA, or fingerprints) is verified."
            )

        paragraphs.append(
            "Note: This rationale is an automated decision-support summary. Final identification remains an authorized human forensic decision."
        )

        return "\n\n".join(paragraphs)

    @staticmethod
    async def generate_rationale(
        candidate_data: Dict[str, Any],
        db: Optional[Session] = None,
    ) -> str:
        """
        Sends structured evidence package to IBM Bob Rationale Agent with fallback.
        """
        prompt = (
            "You are the IBM Bob DVI Forensic Rationale Agent. "
            "Write an objective, clear forensic rationale based ONLY on the provided structured comparison data. "
            "Never invent facts, probabilities, or identify the deceased autonomously. "
            "Explicitly distinguish: 1) observed matching evidence, 2) contradictions, and 3) missing data."
        )

        api_result = await bob_client.call_bob_api(
            agent_name="RATIONALE",
            payload={
                "candidate_evidence": candidate_data,
                "instruction": prompt,
            },
            db=db,
        )

        if api_result.get("success") and "data" in api_result:
            rationale_text = api_result["data"].get("rationale") or api_result["data"].get("response")
            if rationale_text:
                return str(rationale_text)

        return BobRationaleService._generate_local_rationale(candidate_data)
