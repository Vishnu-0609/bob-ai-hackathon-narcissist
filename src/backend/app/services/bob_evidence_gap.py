from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.services.bob_client import bob_client


class BobEvidenceGapService:
    @staticmethod
    def _local_evidence_gaps(candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determines evidence gaps and recommended verification workflows from structured comparison data.
        """
        supporting = candidate_data.get("supporting_evidence", [])
        contradictions = candidate_data.get("contradictions", [])
        unknown = candidate_data.get("unknown", [])

        available: List[str] = [item.get("field_name", "").replace("_", " ").title() for item in supporting]
        missing: List[str] = [item.get("field_name", "").replace("_", " ").title() for item in unknown]
        conflicts: List[str] = [
            f"{c.get('field_name', '').replace('_', ' ').title()}: {c.get('notes', 'Conflict observed')}"
            for c in contradictions
        ]

        recommendations: List[str] = []

        if any("dental" in item.get("field_name", "") for item in unknown):
            recommendations.append("Obtain specialized post-mortem dental charting or ante-mortem odontological records.")

        if any("fingerprint" in item.get("field_name", "") for item in unknown) or candidate_data.get("data_completeness", 0) < 60:
            recommendations.append("Conduct comparative ten-print / dactyloscopic examination if friction ridges are preserved.")

        if contradictions:
            recommendations.append("Perform physical re-examination of anatomical conflict areas with senior forensic pathologist.")

        if candidate_data.get("match_score", 0) >= 75 and not any("dental" in f for f in available):
            recommendations.append("Collect familial reference buccal swabs for STR/DNA profiling confirmation.")

        if not recommendations:
            recommendations.append("Standard secondary verification protocol complete. Proceed with coordinator case review.")

        return {
            "available_evidence": available,
            "missing_evidence": missing,
            "unresolved_contradictions": conflicts,
            "recommended_workflow": recommendations,
            "summary": (
                f"Candidate exhibits {len(available)} confirmed attributes and {len(missing)} missing attributes. "
                f"{len(conflicts)} contradiction(s) require resolution."
            ),
        }

    @staticmethod
    async def analyze_evidence_gaps(
        candidate_data: Dict[str, Any],
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Executes Evidence-Gap analysis with IBM Bob agent and local fallback.
        """
        prompt = (
            "You are the IBM Bob Evidence Gap Agent. "
            "Analyze the structured forensic comparison package. "
            "Identify missing evidence categories and suggest actionable forensic verification steps."
        )

        api_result = await bob_client.call_bob_api(
            agent_name="EVIDENCE_GAP",
            payload={"candidate_evidence": candidate_data, "instruction": prompt},
            db=db,
        )

        if api_result.get("success") and "data" in api_result:
            return api_result["data"]

        return BobEvidenceGapService._local_evidence_gaps(candidate_data)
