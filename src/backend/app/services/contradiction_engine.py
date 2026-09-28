from typing import Dict, Any, List, Optional, Tuple


class ContradictionEngine:
    """
    Dedicated engine for identifying forensic incompatibilities and contradictions.
    CRITICAL RULE: Missing information is NEVER treated as contradictory.
    """

    @staticmethod
    def detect_contradictions(am_case: Any, pm_case: Any) -> Dict[str, Any]:
        contradictions: List[Dict[str, Any]] = []
        negative_evidence: List[Dict[str, Any]] = []
        unknown_fields: List[str] = []

        # 1. Sex Contradiction
        am_sex = (am_case.sex or "").strip().upper()
        pm_sex = (pm_case.sex or "").strip().upper()

        if not am_sex or not pm_sex:
            unknown_fields.append("sex")
        elif am_sex != pm_sex:
            contradictions.append({
                "field": "sex",
                "severity": "STRONG_CONTRADICTION",
                "am_value": am_sex,
                "pm_value": pm_sex,
                "explanation": f"Biological sex mismatch: Ante-mortem recorded as '{am_sex}' while post-mortem examination noted '{pm_sex}'.",
            })

        # 2. Blood Group Contradiction
        am_bg = (am_case.blood_group or "").strip().upper()
        pm_bg = (pm_case.blood_group or "").strip().upper()

        if not am_bg or not pm_bg:
            unknown_fields.append("blood_group")
        elif am_bg != pm_bg:
            contradictions.append({
                "field": "blood_group",
                "severity": "STRONG_CONTRADICTION",
                "am_value": am_bg,
                "pm_value": pm_bg,
                "explanation": f"Blood group incompatibility: AM is '{am_bg}' vs PM is '{pm_bg}'.",
            })

        # 3. Height Discrepancy (> 15 cm is a severe contradiction, > 8 cm is negative evidence)
        am_h = am_case.height_cm
        pm_h = pm_case.height_cm

        if am_h is None or pm_h is None:
            unknown_fields.append("height")
        else:
            diff = abs(am_h - pm_h)
            if diff > 15.0:
                contradictions.append({
                    "field": "height",
                    "severity": "CONTRADICTION",
                    "am_value": f"{am_h} cm",
                    "pm_value": f"{pm_h} cm",
                    "explanation": f"Stature difference of {diff:.1f} cm exceeds acceptable physiological/measurement error threshold (>15 cm).",
                })
            elif diff > 8.0:
                negative_evidence.append({
                    "field": "height",
                    "severity": "NEGATIVE_EVIDENCE",
                    "am_value": f"{am_h} cm",
                    "pm_value": f"{pm_h} cm",
                    "explanation": f"Stature variance of {diff:.1f} cm is outside typical variation.",
                })

        # 4. Age Discrepancy
        am_age = am_case.age
        pm_min = pm_case.estimated_age_min
        pm_max = pm_case.estimated_age_max

        if am_age is None or (pm_min is None and pm_max is None):
            unknown_fields.append("age")
        else:
            min_bound = pm_min if pm_min is not None else 0
            max_bound = pm_max if pm_max is not None else 120
            # Allow a margin of +/- 5 years beyond estimated min/max
            if am_age < (min_bound - 10) or am_age > (max_bound + 10):
                contradictions.append({
                    "field": "age",
                    "severity": "CONTRADICTION",
                    "am_value": f"{am_age} years",
                    "pm_value": f"{min_bound}-{max_bound} years",
                    "explanation": f"Reported AM age ({am_age}) is significantly outside estimated PM range ({min_bound}-{max_bound}).",
                })
            elif am_age < min_bound or am_age > max_bound:
                negative_evidence.append({
                    "field": "age",
                    "severity": "NEGATIVE_EVIDENCE",
                    "am_value": f"{am_age} years",
                    "pm_value": f"{min_bound}-{max_bound} years",
                    "explanation": f"Reported AM age ({am_age}) is slightly outside PM range ({min_bound}-{max_bound}).",
                })

        # 5. Tattoo Location Mismatch
        am_tattoos = am_case.tattoos or []
        pm_tattoos = pm_case.tattoos or []

        if not am_tattoos or not pm_tattoos:
            if not am_tattoos and not pm_tattoos:
                pass
            else:
                unknown_fields.append("tattoos")
        else:
            # Check if locations explicitly conflict
            am_locs = {
                t.get("location", "").lower().strip()
                for t in am_tattoos
                if isinstance(t, dict) and t.get("location")
            }
            pm_locs = {
                t.get("location", "").lower().strip()
                for t in pm_tattoos
                if isinstance(t, dict) and t.get("location")
            }
            if am_locs and pm_locs:
                overlap = am_locs.intersection(pm_locs)
                if not overlap and len(am_locs) > 0 and len(pm_locs) > 0:
                    negative_evidence.append({
                        "field": "tattoos",
                        "severity": "NEGATIVE_EVIDENCE",
                        "am_value": ", ".join(am_locs),
                        "pm_value": ", ".join(pm_locs),
                        "explanation": f"Tattoo locations do not align: AM specifies [{', '.join(am_locs)}] while PM notes [{', '.join(pm_locs)}].",
                    })

        # Determine overall status
        if any(c["severity"] == "STRONG_CONTRADICTION" for c in contradictions):
            status = "STRONG_CONTRADICTION"
        elif contradictions:
            status = "CONTRADICTION_REVIEW"
        elif negative_evidence:
            status = "CONTRADICTION_REVIEW"
        else:
            status = "NONE"

        return {
            "contradiction_status": status,
            "contradictions": contradictions,
            "negative_evidence": negative_evidence,
            "unknown_fields": unknown_fields,
        }
