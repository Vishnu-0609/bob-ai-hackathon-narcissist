import re
from typing import Dict, Any, List, Optional, Tuple
from app.core.config import settings
from app.services.contradiction_engine import ContradictionEngine


class MatchingEngine:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "sex": settings.WEIGHT_SEX,
            "age": settings.WEIGHT_AGE,
            "height": settings.WEIGHT_HEIGHT,
            "blood_group": settings.WEIGHT_BLOOD_GROUP,
            "scars": settings.WEIGHT_SCARS,
            "birthmarks": settings.WEIGHT_BIRTHMARKS,
            "tattoos": settings.WEIGHT_TATTOOS,
            "clothing": settings.WEIGHT_CLOTHING,
            "jewellery": settings.WEIGHT_JEWELLERY,
            "dental": settings.WEIGHT_DENTAL,
            "medical_implants": settings.WEIGHT_MEDICAL_IMPLANTS,
            "location_time": settings.WEIGHT_LOCATION_TIME,
        }

    def _normalize_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.lower().strip())

    def compare_sex(self, am_case: Any, pm_case: Any) -> Dict[str, Any]:
        weight = self.weights["sex"]
        am_val = (am_case.sex or "").strip().upper()
        pm_val = (pm_case.sex or "").strip().upper()

        if not am_val or not pm_val:
            return {
                "field_name": "sex",
                "am_value": am_val or "Not recorded",
                "pm_value": pm_val or "Not recorded",
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": "Sex information unavailable in one or both records.",
            }

        if am_val == pm_val:
            return {
                "field_name": "sex",
                "am_value": am_val,
                "pm_value": pm_val,
                "comparison_result": "MATCH",
                "weight": weight,
                "score_awarded": weight,
                "contradiction": False,
                "notes": f"Biological sex match ({am_val}).",
            }
        else:
            return {
                "field_name": "sex",
                "am_value": am_val,
                "pm_value": pm_val,
                "comparison_result": "MISMATCH",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": True,
                "notes": f"Sex mismatch: AM ({am_val}) vs PM ({pm_val}).",
            }

    def compare_age(self, am_case: Any, pm_case: Any) -> Dict[str, Any]:
        weight = self.weights["age"]
        am_age = am_case.age
        pm_min = pm_case.estimated_age_min
        pm_max = pm_case.estimated_age_max

        am_str = f"{am_age} yrs" if am_age is not None else "Not recorded"
        pm_str = f"{pm_min}-{pm_max} yrs" if (pm_min and pm_max) else (f"{pm_min or pm_max} yrs" if (pm_min or pm_max) else "Not recorded")

        if am_age is None or (pm_min is None and pm_max is None):
            return {
                "field_name": "age",
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": "Age information unavailable in one or both records.",
            }

        min_val = pm_min if pm_min is not None else pm_max
        max_val = pm_max if pm_max is not None else pm_min

        if min_val <= am_age <= max_val:
            return {
                "field_name": "age",
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "MATCH",
                "weight": weight,
                "score_awarded": weight,
                "contradiction": False,
                "notes": f"AM age ({am_age}) falls within PM estimated range ({min_val}-{max_val}).",
            }
        elif (min_val - 4) <= am_age <= (max_val + 4):
            score = round(weight * 0.7, 1)
            return {
                "field_name": "age",
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "MATCH",
                "weight": weight,
                "score_awarded": score,
                "contradiction": False,
                "notes": f"AM age ({am_age}) is compatible within minor margin of PM range ({min_val}-{max_val}).",
            }
        else:
            diff = min(abs(am_age - min_val), abs(am_age - max_val))
            is_contradiction = diff > 10
            return {
                "field_name": "age",
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "MISMATCH",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": is_contradiction,
                "notes": f"AM age ({am_age}) deviates by {diff} yrs from PM range ({min_val}-{max_val}).",
            }

    def compare_height(self, am_case: Any, pm_case: Any) -> Dict[str, Any]:
        weight = self.weights["height"]
        am_h = am_case.height_cm
        pm_h = pm_case.height_cm

        am_str = f"{am_h:.0f} cm" if am_h else "Not recorded"
        pm_str = f"{pm_h:.0f} cm" if pm_h else "Not recorded"

        if am_h is None or pm_h is None:
            return {
                "field_name": "height",
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": "Height measurement missing from one or both records.",
            }

        diff = abs(am_h - pm_h)
        if diff <= 3.0:
            return {
                "field_name": "height",
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "MATCH",
                "weight": weight,
                "score_awarded": weight,
                "contradiction": False,
                "notes": f"Stature closely matches within {diff:.1f} cm.",
            }
        elif diff <= 7.0:
            score = round(weight * 0.7, 1)
            return {
                "field_name": "height",
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "MATCH",
                "weight": weight,
                "score_awarded": score,
                "contradiction": False,
                "notes": f"Stature compatible within acceptable forensic variance ({diff:.1f} cm diff).",
            }
        elif diff <= 15.0:
            score = round(weight * 0.3, 1)
            return {
                "field_name": "height",
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "MISMATCH",
                "weight": weight,
                "score_awarded": score,
                "contradiction": False,
                "notes": f"Moderate stature variance ({diff:.1f} cm difference).",
            }
        else:
            return {
                "field_name": "height",
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "MISMATCH",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": True,
                "notes": f"Severe height discrepancy: {diff:.1f} cm difference.",
            }

    def compare_blood_group(self, am_case: Any, pm_case: Any) -> Dict[str, Any]:
        weight = self.weights["blood_group"]
        am_bg = (am_case.blood_group or "").strip().upper()
        pm_bg = (pm_case.blood_group or "").strip().upper()

        if not am_bg or not pm_bg:
            return {
                "field_name": "blood_group",
                "am_value": am_bg or "Not recorded",
                "pm_value": pm_bg or "Not recorded",
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": "Serology/blood group not available in both records.",
            }

        if am_bg == pm_bg:
            return {
                "field_name": "blood_group",
                "am_value": am_bg,
                "pm_value": pm_bg,
                "comparison_result": "MATCH",
                "weight": weight,
                "score_awarded": weight,
                "contradiction": False,
                "notes": f"Identical blood group ({am_bg}).",
            }
        else:
            return {
                "field_name": "blood_group",
                "am_value": am_bg,
                "pm_value": pm_bg,
                "comparison_result": "MISMATCH",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": True,
                "notes": f"Blood group contradiction: AM ({am_bg}) vs PM ({pm_bg}).",
            }

    def _compare_feature_list(
        self,
        am_items: List[Any],
        pm_items: List[Any],
        field_name: str,
        weight: float,
    ) -> Dict[str, Any]:
        def format_item(x: Any) -> str:
            if isinstance(x, dict):
                desc = x.get("description") or x.get("mark_type") or "feature"
                loc = x.get("location")
                return f"{desc} ({loc})" if loc and loc not in desc else desc
            return str(x)

        am_str = ", ".join([format_item(x) for x in am_items]) if am_items else "None recorded"
        pm_str = ", ".join([format_item(x) for x in pm_items]) if pm_items else "None recorded"

        # Capture provenance if attached to any item
        provenance = {}
        for item in (am_items or []) + (pm_items or []):
            if isinstance(item, dict) and "provenance" in item:
                provenance = item["provenance"]
                break

        if not am_items and not pm_items:
            return {
                "field_name": field_name,
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "NOT_AVAILABLE",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": f"No {field_name} documented in either record.",
                "provenance": provenance,
            }

        if not am_items or not pm_items:
            return {
                "field_name": field_name,
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": f"{field_name.capitalize()} present in one record but unobserved/unreported in the other.",
                "provenance": provenance,
            }

        # Compare elements
        matched_elements = 0.0
        total_elements = len(am_items)
        match_reasons = []

        for a in am_items:
            a_loc = self._normalize_text(a.get("location", str(a)) if isinstance(a, dict) else str(a))
            a_desc = self._normalize_text(a.get("description", "") if isinstance(a, dict) else "")
            a_motifs = [self._normalize_text(m) for m in (a.get("design_motifs", []) if isinstance(a, dict) else [])]

            best_match_for_a = 0.0
            best_reason_for_a = ""

            for p in pm_items:
                p_loc = self._normalize_text(p.get("location", str(p)) if isinstance(p, dict) else str(p))
                p_desc = self._normalize_text(p.get("description", "") if isinstance(p, dict) else "")
                p_motifs = [self._normalize_text(m) for m in (p.get("design_motifs", []) if isinstance(p, dict) else [])]

                # Check anatomical location match (e.g. left forearm, shoulder)
                loc_matched = False
                if a_loc and p_loc:
                    loc_tokens_a = set(a_loc.split()) - {"on", "the", "near", "side", "area", "region"}
                    loc_tokens_p = set(p_loc.split()) - {"on", "the", "near", "side", "area", "region"}
                    if loc_tokens_a.intersection(loc_tokens_p) or a_loc in p_loc or p_loc in a_loc:
                        loc_matched = True

                # Check motif / description match
                desc_matched = False
                desc_tokens_a = set(a_desc.split()) - {"a", "an", "the", "and", "tattoo", "scar", "mark", "visible"}
                desc_tokens_p = set(p_desc.split()) - {"a", "an", "the", "and", "tattoo", "scar", "mark", "visible"}
                if desc_tokens_a.intersection(desc_tokens_p) or (a_desc and p_desc and (a_desc in p_desc or p_desc in a_desc)):
                    desc_matched = True
                if any(m in p_motifs or m in p_desc for m in a_motifs):
                    desc_matched = True

                if loc_matched and desc_matched:
                    if 1.0 > best_match_for_a:
                        best_match_for_a = 1.0
                        best_reason_for_a = f"Location and feature match ({a_loc})"
                elif loc_matched:
                    if 0.8 > best_match_for_a:
                        best_match_for_a = 0.8
                        best_reason_for_a = f"Location match ({a_loc})"
                elif desc_matched:
                    if 0.7 > best_match_for_a:
                        best_match_for_a = 0.7
                        best_reason_for_a = f"Feature motif match"

            matched_elements += best_match_for_a
            if best_reason_for_a:
                match_reasons.append(best_reason_for_a)

        if matched_elements > 0:
            ratio = min(1.0, matched_elements / max(1, total_elements))
            score = round(weight * ratio, 1)
            reason_str = f" ({'; '.join(set(match_reasons))})" if match_reasons else ""
            return {
                "field_name": field_name,
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "MATCH",
                "weight": weight,
                "score_awarded": score,
                "contradiction": False,
                "notes": f"{field_name.capitalize()} features match{reason_str}.",
                "provenance": provenance,
            }
        else:
            return {
                "field_name": field_name,
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "MISMATCH",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": f"Differing recorded {field_name} details.",
                "provenance": provenance,
            }

    def _compare_text_list(
        self,
        am_list: List[Any],
        pm_list: List[Any],
        field_name: str,
        weight: float,
    ) -> Dict[str, Any]:
        def format_text_item(x: Any) -> str:
            if isinstance(x, dict):
                desc = x.get("description") or f"{x.get('color', '')} {x.get('item_type', '')}".strip()
                return desc or "item"
            return str(x)

        am_str = ", ".join([format_text_item(x) for x in am_list]) if am_list else "None recorded"
        pm_str = ", ".join([format_text_item(x) for x in pm_list]) if pm_list else "None recorded"

        provenance = {}
        for item in (am_list or []) + (pm_list or []):
            if isinstance(item, dict) and "provenance" in item:
                provenance = item["provenance"]
                break

        if not am_list and not pm_list:
            return {
                "field_name": field_name,
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "NOT_AVAILABLE",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": f"No {field_name} observed in either case.",
                "provenance": provenance,
            }

        if not am_list or not pm_list:
            return {
                "field_name": field_name,
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": f"{field_name.capitalize()} data missing in one case.",
                "provenance": provenance,
            }

        am_tokens = set(re.findall(r"\w+", self._normalize_text(am_str)))
        pm_tokens = set(re.findall(r"\w+", self._normalize_text(pm_str)))
        common = am_tokens.intersection(pm_tokens)

        # Ignore common stopwords
        stopwords = {"and", "with", "the", "for", "worn", "item", "color", "colored", "pattern", "description", "status", "observed", "inferred", "unknown"}
        common = {w for w in common if len(w) > 2 and w not in stopwords}

        if common:
            # Full or proportional score based on keyword overlap
            score = weight
            return {
                "field_name": field_name,
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "MATCH",
                "weight": weight,
                "score_awarded": score,
                "contradiction": False,
                "notes": f"Compatible {field_name} articles identified (matching keywords: {', '.join(sorted(common))}).",
                "provenance": provenance,
            }
        else:
            return {
                "field_name": field_name,
                "am_value": am_str,
                "pm_value": pm_str,
                "comparison_result": "MISMATCH",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": f"Differing {field_name} records.",
                "provenance": provenance,
            }


    def compare_dental(self, am_case: Any, pm_case: Any) -> Dict[str, Any]:
        weight = self.weights["dental"]
        am_d = (am_case.dental_notes or "").strip()
        pm_d = (pm_case.dental_findings or "").strip()

        if not am_d and not pm_d:
            return {
                "field_name": "dental",
                "am_value": "No dental records",
                "pm_value": "No dental exam",
                "comparison_result": "NOT_AVAILABLE",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": "Odontological records unavailable for both cases.",
            }

        if not am_d or not pm_d:
            return {
                "field_name": "dental",
                "am_value": am_d or "No dental records",
                "pm_value": pm_d or "No dental exam",
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": "Dental record exists in one case only. Pending comparative dental charting.",
            }

        am_norm = self._normalize_text(am_d)
        pm_norm = self._normalize_text(pm_d)

        # Look for matching dental markers (crown, filling, molar, missing, gold, extraction, etc.)
        tokens_am = set(re.findall(r"\w+", am_norm))
        tokens_pm = set(re.findall(r"\w+", pm_norm))
        overlap = tokens_am.intersection(tokens_pm) - {"the", "and", "teeth", "tooth", "present", "dental", "with"}

        if len(overlap) >= 1:
            return {
                "field_name": "dental",
                "am_value": am_d,
                "pm_value": pm_d,
                "comparison_result": "MATCH",
                "weight": weight,
                "score_awarded": weight,
                "contradiction": False,
                "notes": f"Odontological concordance on features: {', '.join(overlap)}.",
            }
        else:
            return {
                "field_name": "dental",
                "am_value": am_d,
                "pm_value": pm_d,
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": "Different descriptive terms in dental records. Requires specialist odontologist review.",
            }

    def compare_medical(self, am_case: Any, pm_case: Any) -> Dict[str, Any]:
        weight = self.weights["medical_implants"]
        am_m = (am_case.medical_history or "").strip()
        pm_m = (pm_case.medical_findings or "").strip()

        if not am_m and not pm_m:
            return {
                "field_name": "medical_implants",
                "am_value": "None recorded",
                "pm_value": "None noted",
                "comparison_result": "NOT_AVAILABLE",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": "No unique surgical or implant history noted.",
            }

        if not am_m or not pm_m:
            return {
                "field_name": "medical_implants",
                "am_value": am_m or "None recorded",
                "pm_value": pm_m or "None noted",
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": "Medical history incomplete across cases.",
            }

        am_norm = self._normalize_text(am_m)
        pm_norm = self._normalize_text(pm_m)
        overlap = set(am_norm.split()).intersection(set(pm_norm.split())) - {"surgery", "the", "and", "of", "in"}

        if overlap:
            return {
                "field_name": "medical_implants",
                "am_value": am_m,
                "pm_value": pm_m,
                "comparison_result": "MATCH",
                "weight": weight,
                "score_awarded": weight,
                "contradiction": False,
                "notes": f"Compatible medical observations: {', '.join(overlap)}.",
            }
        else:
            return {
                "field_name": "medical_implants",
                "am_value": am_m,
                "pm_value": pm_m,
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": "Medical details require specialist correlation.",
            }

    def compare_location(self, am_case: Any, pm_case: Any) -> Dict[str, Any]:
        weight = self.weights["location_time"]
        am_loc = (am_case.last_seen_location or "").strip()
        pm_loc = (pm_case.recovery_location or "").strip()

        if not am_loc or not pm_loc:
            return {
                "field_name": "location_time",
                "am_value": am_loc or "Not recorded",
                "pm_value": pm_loc or "Not recorded",
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": "Location tracking data partial or missing.",
            }

        am_norm = self._normalize_text(am_loc)
        pm_norm = self._normalize_text(pm_loc)
        overlap = set(am_norm.split()).intersection(set(pm_norm.split())) - {"coach", "train", "station", "near", "at", "the"}

        if overlap or am_norm in pm_norm or pm_norm in am_norm:
            return {
                "field_name": "location_time",
                "am_value": am_loc,
                "pm_value": pm_loc,
                "comparison_result": "MATCH",
                "weight": weight,
                "score_awarded": weight,
                "contradiction": False,
                "notes": f"Plausible geographic/sector correlation ({am_loc} <-> {pm_loc}).",
            }
        else:
            return {
                "field_name": "location_time",
                "am_value": am_loc,
                "pm_value": pm_loc,
                "comparison_result": "UNKNOWN",
                "weight": weight,
                "score_awarded": 0.0,
                "contradiction": False,
                "notes": f"Different incident recovery sectors ({am_loc} vs {pm_loc}).",
            }

    def evaluate_pair(self, pm_case: Any, am_case: Any) -> Dict[str, Any]:
        """
        Calculates deterministic comparison, score (0-100), contradictions, and evidence items.
        """
        evidence_items: List[Dict[str, Any]] = [
            self.compare_sex(am_case, pm_case),
            self.compare_age(am_case, pm_case),
            self.compare_height(am_case, pm_case),
            self.compare_blood_group(am_case, pm_case),
            self._compare_feature_list(am_case.scars or [], pm_case.scars or [], "scars", self.weights["scars"]),
            self._compare_feature_list(am_case.birthmarks or [], pm_case.birthmarks or [], "birthmarks", self.weights["birthmarks"]),
            self._compare_feature_list(am_case.tattoos or [], pm_case.tattoos or [], "tattoos", self.weights["tattoos"]),
            self._compare_text_list(am_case.clothing or [], pm_case.clothing or [], "clothing", self.weights["clothing"]),
            self._compare_text_list(am_case.jewellery or [], pm_case.jewellery or [], "jewellery", self.weights["jewellery"]),
            self.compare_dental(am_case, pm_case),
            self.compare_medical(am_case, pm_case),
            self.compare_location(am_case, pm_case),
        ]

        # Calculate Raw Score
        raw_score = sum(item["score_awarded"] for item in evidence_items)
        match_score = round(min(100.0, max(0.0, raw_score)), 1)

        # Categorize Evidence
        supporting = [item for item in evidence_items if item["comparison_result"] == "MATCH"]
        contradictions_list = [item for item in evidence_items if item["contradiction"]]
        unknown = [item for item in evidence_items if item["comparison_result"] in ("UNKNOWN", "NOT_AVAILABLE")]

        # Contradiction Engine Check
        contra_result = ContradictionEngine.detect_contradictions(am_case, pm_case)
        contra_status = contra_result["contradiction_status"]

        # If strong contradiction exists, penalize score and flag
        if contra_status == "STRONG_CONTRADICTION":
            match_score = round(match_score * 0.4, 1)

        # Calculate Data Completeness (fields with data in both)
        valid_fields = sum(1 for item in evidence_items if item["comparison_result"] in ("MATCH", "MISMATCH"))
        data_completeness = round((valid_fields / len(evidence_items)) * 100.0, 1)

        # Calculate Evidence Quality
        primary_evidence_score = sum(
            item["score_awarded"]
            for item in evidence_items
            if item["field_name"] in ("scars", "tattoos", "dental", "blood_group")
        )
        if primary_evidence_score >= 20 and data_completeness >= 60:
            evidence_quality = "HIGH"
        elif primary_evidence_score >= 10 and data_completeness >= 40:
            evidence_quality = "MEDIUM"
        elif data_completeness < 25:
            evidence_quality = "INSUFFICIENT"
        else:
            evidence_quality = "LOW"

        # Determine Candidate Status
        if contra_status == "STRONG_CONTRADICTION" or contra_status == "CONTRADICTION_REVIEW":
            status = "CONTRADICTION_REVIEW"
        elif match_score >= settings.STRONG_CANDIDATE_THRESHOLD:
            status = "STRONG_CANDIDATE"
        elif match_score >= settings.MODERATE_CANDIDATE_THRESHOLD:
            status = "MODERATE_CANDIDATE"
        elif evidence_quality == "INSUFFICIENT" or match_score < 30:
            status = "INSUFFICIENT_EVIDENCE"
        else:
            status = "MODERATE_CANDIDATE"

        return {
            "pm_id": str(pm_case.id),
            "pm_body_number": str(pm_case.body_number),
            "am_id": str(am_case.id),
            "am_case_number": str(am_case.case_number),
            "am_name": str(am_case.name),
            "match_score": match_score,
            "evidence_quality": evidence_quality,
            "data_completeness": data_completeness,
            "contradiction_status": contra_status,
            "status": status,
            "evidence_items": evidence_items,
            "supporting_evidence": supporting,
            "contradictions": contradictions_list,
            "unknown": unknown,
            "contradiction_details": contra_result,
        }
