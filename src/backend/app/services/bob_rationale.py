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

        target_name = f" — *{am_name}*" if am_name and am_name != "Unknown" else ""

        # Score badge
        if score >= 80:
            score_label = "🟢 Strong Candidate"
        elif score >= 50:
            score_label = "🟡 Moderate Candidate"
        else:
            score_label = "🔴 Weak Candidate"

        lines = []

        # Header
        lines.append(f"## Match Summary: {am_num}{target_name} ↔ {pm_num}")
        lines.append(f"> **Score: {score}/100** &nbsp;|&nbsp; {score_label} &nbsp;|&nbsp; Evidence Quality: **{quality}**")
        lines.append("")

        # Supporting evidence
        if matched_fields:
            lines.append("### ✅ Supporting Evidence")
            for item in supporting:
                f_name = item.get("field_name", "")
                am_val = item.get("am_value", "")
                pm_val = item.get("pm_value", "")
                label = f_name.replace("_", " ").title()
                if f_name == "scars":
                    detail = f"Scar pattern on record matches — *{am_val}*"
                elif f_name == "tattoos":
                    detail = f"Tattoo features align — *{am_val}*"
                elif f_name == "dental":
                    detail = f"Odontological findings are concordant — *{am_val}*"
                elif f_name in ("sex", "blood_group"):
                    detail = f"{label} is consistent — `{am_val}`"
                elif f_name in ("age", "height"):
                    detail = f"{label} falls within compatible range — AM `{am_val}` vs PM `{pm_val}`"
                elif f_name == "clothing":
                    detail = f"Recovered clothing matches reported description — *{am_val}*"
                else:
                    detail = f"{label} is aligned between records"
                lines.append(f"- {detail}")
            lines.append("")
        else:
            lines.append("### ✅ Supporting Evidence")
            lines.append("- No direct matching attributes were identified in this comparison.")
            lines.append("")

        # Contradictions
        lines.append("### ⚠️ Contradictions")
        if contradicted_fields:
            for item in contradictions:
                f_name = item.get("field_name", "").replace("_", " ").title()
                note = item.get("notes", "Discrepancy observed")
                lines.append(f"- **{f_name}:** {note}")
            lines.append("")
            lines.append("> 🔴 **These discrepancies must be resolved before this case can proceed to reconciliation.**")
        else:
            lines.append("- No anatomical or biological contradictions detected.")
        lines.append("")

        # Missing evidence
        if unknown_fields:
            lines.append("### 🔍 Missing / Unverified Evidence")
            missing_names = [f.replace("_", " ").title() for f in unknown_fields[:6]]
            for m in missing_names:
                lines.append(f"- {m}")
            lines.append("")
            lines.append(
                "> This match remains **non-conclusive** until secondary forensic confirmation "
                "(e.g. DNA, comparative dental, or fingerprints) is completed."
            )
            lines.append("")

        # Disclaimer
        lines.append("---")
        lines.append(
            "*⚖️ This is an automated decision-support summary only. "
            "Final identification is a human forensic authority decision and cannot be made by this system.*"
        )

        return "\n".join(lines)

    @staticmethod
    async def generate_rationale(
        candidate_data: Dict[str, Any],
        db: Optional[Session] = None,
    ) -> str:
        """
        Sends structured evidence package to IBM Bob Rationale Agent with fallback.
        """
        prompt = (
            "You are Bob, a forensic assistant helping DVI coordinators understand candidate match results.\n\n"
            "Your job is to explain — clearly and conversationally — why a particular ante-mortem (AM) profile "
            "is ranked as a candidate for a post-mortem (PM) record, based strictly on the structured data provided.\n\n"
            "Format your response using markdown with these sections:\n"
            "1. **Match Summary** — one short sentence describing the overall picture\n"
            "2. **What lines up** — bullet list of matching evidence points\n"
            "3. **Points of concern** — any contradictions or red flags\n"
            "4. **What's still missing** — evidence gaps that need follow-up\n"
            "5. **Next steps** — 1-2 recommended actions for the coordinator\n\n"
            "Do not invent facts. Do not assign probability of identity. "
            "Only reference what is explicitly in the data."
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
