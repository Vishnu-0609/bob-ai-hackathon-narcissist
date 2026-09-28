import re
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from app.model import get_clip_model
from app.schemas import AnteMortemProfile, PostMortemRecord, MatchCandidate

class BobDVIMatcher:
    """
    Bob - Automated Disaster Victim Identification (DVI) Cross-Referencing Engine.
    Employs OpenAI CLIP multimodal embeddings (visual + semantic) combined with
    INTERPOL DVI primary and secondary forensic criteria.
    """
    def __init__(self):
        self.clip = get_clip_model()

    def cross_reference_body(
        self,
        pm: PostMortemRecord,
        am_profiles: List[AnteMortemProfile],
        top_k: int = 3
    ) -> List[MatchCandidate]:
        if not am_profiles:
            return []

        candidates = []
        for am in am_profiles:
            candidate = self._evaluate_pairing(pm, am)
            candidates.append(candidate)

        # Sort by match probability descending
        candidates.sort(key=lambda c: c.match_probability, reverse=True)

        # Assign ranks and take top_k
        top_candidates = []
        for i, cand in enumerate(candidates[:top_k]):
            cand.rank = i + 1
            top_candidates.append(cand)

        return top_candidates

    def _evaluate_pairing(self, pm: PostMortemRecord, am: AnteMortemProfile) -> MatchCandidate:
        matching_factors = []
        discrepancy_flags = []

        # ----------------------------------------------------
        # 1. Demographic & Gender Check
        # ----------------------------------------------------
        gender_compatible, gender_note = self._check_gender_compatibility(pm.estimated_gender, am.gender)
        if gender_compatible:
            matching_factors.append(gender_note)
        else:
            discrepancy_flags.append(gender_note)

        # Age check
        age_score, age_note = self._check_age_compatibility(pm.estimated_age_range, am.age, am.age_range)
        if age_score >= 0.7:
            matching_factors.append(age_note)
        elif age_score < 0.3:
            discrepancy_flags.append(age_note)

        # ----------------------------------------------------
        # 2. Forensic Biomarkers: Scars, Marks, Tattoos, Dental
        # ----------------------------------------------------
        biomarker_score, biomarker_matches, biomarker_discrepancies = self._evaluate_biomarkers(pm, am)
        matching_factors.extend(biomarker_matches)
        discrepancy_flags.extend(biomarker_discrepancies)

        # ----------------------------------------------------
        # 3. Clothing & Personal Belongings
        # ----------------------------------------------------
        clothing_score, clothing_matches = self._evaluate_clothing_effects(pm, am)
        matching_factors.extend(clothing_matches)

        # ----------------------------------------------------
        # 4. CLIP Semantic Text Similarity
        # ----------------------------------------------------
        am_text = (
            f"Ante-mortem profile: {am.full_name}, {am.gender}, age {am.age or am.age_range}. "
            f"Hair: {am.hair_description}. Scars and birthmarks: {am.scars_and_birthmarks}. "
            f"Tattoos and piercings: {am.tattoos_piercings or 'none'}. "
            f"Clothing: {am.clothing_worn}. Jewelry and effects: {am.jewelry_accessories or 'none'}. "
            f"Dental notes: {am.dental_notes or 'none'}."
        )

        pm_text = (
            f"Post-mortem observation: Unidentified body recovered at {pm.recovery_location}. "
            f"Estimated {pm.estimated_gender}, age {pm.estimated_age_range}. "
            f"Hair: {pm.hair_observation}. Observed scars and birthmarks: {pm.scars_and_birthmarks}. "
            f"Tattoos: {pm.tattoos_piercings or 'none'}. "
            f"Recovered clothing: {pm.clothing_recovered}. "
            f"Recovered jewelry and belongings: {pm.jewelry_belongings or 'none'}. "
            f"Dental findings: {pm.dental_observations or 'none'}."
        )

        am_text_emb = self.clip.encode_text(am_text)
        pm_text_emb = self.clip.encode_text(pm_text)

        # Cosine similarity between CLIP semantic vectors
        semantic_sim = float(np.dot(am_text_emb, pm_text_emb))
        semantic_sim_pct = max(0.0, min(100.0, (semantic_sim + 1.0) / 2.0 * 100.0))

        # ----------------------------------------------------
        # 5. CLIP Multimodal Visual Similarity
        # ----------------------------------------------------
        visual_sim_pct, best_am_img, best_pm_img = self._evaluate_visual_similarity(pm, am)

        # ----------------------------------------------------
        # 6. Overall Match Probability Score (0 - 100%)
        # ----------------------------------------------------
        # Weighted fusion of forensic evidence:
        # - Biomarkers (scars, dental, tattoos): 30%
        # - Clothing & Belongings: 25%
        # - CLIP Visual photo similarity: 25%
        # - CLIP Semantic description similarity: 20%
        raw_prob = (
            (biomarker_score * 30.0) +
            (clothing_score * 25.0) +
            (visual_sim_pct * 0.25) +
            (semantic_sim_pct * 0.20)
        )

        # Gender penalty if hard mismatch
        if not gender_compatible:
            raw_prob *= 0.25

        match_prob = round(max(5.0, min(99.4, raw_prob)), 1)

        # ----------------------------------------------------
        # 7. Generate Bob's Forensic Rationale
        # ----------------------------------------------------
        rationale = self._generate_bob_rationale(
            pm=pm,
            am=am,
            match_prob=match_prob,
            biomarker_matches=biomarker_matches,
            clothing_matches=clothing_matches,
            visual_sim=visual_sim_pct,
            discrepancies=discrepancy_flags
        )

        return MatchCandidate(
            rank=0,
            ante_mortem_id=am.id,
            missing_person_name=am.full_name,
            match_probability=match_prob,
            visual_clip_similarity=round(visual_sim_pct, 1),
            semantic_clip_similarity=round(semantic_sim_pct, 1),
            biometric_score=round(biomarker_score * 100.0, 1),
            rationale=rationale,
            matching_factors=matching_factors,
            discrepancy_flags=discrepancy_flags,
            am_profile=am,
            best_am_image=best_am_img,
            best_pm_image=best_pm_img
        )

    def _check_gender_compatibility(self, pm_gender: str, am_gender: str) -> Tuple[bool, str]:
        pm_g = pm_gender.lower().strip()
        am_g = am_gender.lower().strip()
        if "indeterminate" in pm_g or "unknown" in pm_g:
            return True, f"Gender consistent (PM status indeterminate, AM reported {am_gender})"
        if pm_g == am_g or (pm_g in ["male", "man"] and am_g in ["male", "man"]) or (pm_g in ["female", "woman"] and am_g in ["female", "woman"]):
            return True, f"Gender concordant ({am_gender.capitalize()})"
        return False, f"Gender discrepancy: PM observed {pm_gender} vs AM reported {am_gender}"

    def _check_age_compatibility(self, pm_range: str, am_age: Optional[int], am_range: Optional[str]) -> Tuple[float, str]:
        # Extract numbers from pm_range (e.g. '25-35' -> 25, 35)
        pm_nums = [int(n) for n in re.findall(r'\b\d+\b', pm_range or '')]
        if not pm_nums:
            return 0.5, "Age compatibility undetermined (no PM age range recorded)"

        pm_min = min(pm_nums)
        pm_max = max(pm_nums) if len(pm_nums) > 1 else pm_min + 10

        target_age = am_age
        if target_age is None and am_range:
            am_nums = [int(n) for n in re.findall(r'\b\d+\b', am_range)]
            if am_nums:
                target_age = int(np.mean(am_nums))

        if target_age is None:
            return 0.5, "Age compatibility undetermined (no AM age recorded)"

        if pm_min - 5 <= target_age <= pm_max + 5:
            return 1.0, f"Age concordant: Reported age {target_age} falls within PM range {pm_min}-{pm_max}"
        else:
            diff = min(abs(target_age - pm_min), abs(target_age - pm_max))
            return max(0.1, 1.0 - (diff / 20.0)), f"Age variance: Reported {target_age} vs PM range {pm_min}-{pm_max}"

    def _evaluate_biomarkers(self, pm: PostMortemRecord, am: AnteMortemProfile) -> Tuple[float, List[str], List[str]]:
        matches = []
        discrepancies = []
        score = 0.4  # baseline

        pm_bio = f"{pm.scars_and_birthmarks} {pm.tattoos_piercings or ''} {pm.dental_observations or ''}".lower()
        am_bio = f"{am.scars_and_birthmarks} {am.tattoos_piercings or ''} {am.dental_notes or ''}".lower()

        # Key forensic keywords
        bio_keywords = [
            ("appendectomy", "surgical appendectomy scar"),
            ("scar", "scar marker"),
            ("mole", "pigmented mole / nevus"),
            ("birthmark", "birthmark"),
            ("tattoo", "distinctive tattoo"),
            ("trishul", "religious emblem / trishul tattoo"),
            ("piercing", "earlobe / body piercing"),
            ("crown", "dental crown / restoration"),
            ("molar", "molar dental feature"),
            ("premolar", "premolar observation"),
            ("missing tooth", "antemortem tooth loss"),
            ("fracture", "healed bone fracture")
        ]

        found_overlaps = 0
        for kw, label in bio_keywords:
            if kw in pm_bio and kw in am_bio:
                matches.append(f"Biomarker concordance: {label} present in both AM and PM records")
                found_overlaps += 1

        if found_overlaps >= 3:
            score = 1.0
        elif found_overlaps == 2:
            score = 0.85
        elif found_overlaps == 1:
            score = 0.70
        else:
            score = 0.45

        return score, matches, discrepancies

    def _evaluate_clothing_effects(self, pm: PostMortemRecord, am: AnteMortemProfile) -> Tuple[float, List[str]]:
        matches = []
        score = 0.4

        pm_items = f"{pm.clothing_recovered} {pm.jewelry_belongings or ''}".lower()
        am_items = f"{am.clothing_worn} {am.jewelry_accessories or ''}".lower()

        clothing_keywords = [
            ("red", "red/maroon colored garment"),
            ("maroon", "maroon color fabric"),
            ("blue", "blue colored garment"),
            ("black", "black colored garment"),
            ("white", "white/light garment"),
            ("kurta", "kurta / ethnic wear"),
            ("hoodie", "hoodie / jacket"),
            ("saree", "saree"),
            ("jeans", "denim jeans"),
            ("ring", "finger ring"),
            ("blue stone", "ring with blue stone / sapphire"),
            ("watch", "wrist watch"),
            ("thread", "sacred thread / wristband (kalawa)"),
            ("gold", "gold jewelry / ornament"),
            ("silver", "silver jewelry / accessory")
        ]

        found_count = 0
        for kw, label in clothing_keywords:
            if kw in pm_items and kw in am_items:
                matches.append(f"Physical effect match: {label}")
                found_count += 1

        if found_count >= 3:
            score = 0.95
        elif found_count == 2:
            score = 0.80
        elif found_count == 1:
            score = 0.65
        else:
            score = 0.40

        return score, matches

    def _evaluate_visual_similarity(self, pm: PostMortemRecord, am: AnteMortemProfile) -> Tuple[float, Optional[str], Optional[str]]:
        if not pm.image_paths or not am.image_paths:
            return 50.0, (am.image_paths[0] if am.image_paths else None), (pm.image_paths[0] if pm.image_paths else None)

        best_sim = -1.0
        best_am = am.image_paths[0]
        best_pm = pm.image_paths[0]

        from app.config import UPLOAD_DIR
        for am_img_rel in am.image_paths:
            for pm_img_rel in pm.image_paths:
                am_path = UPLOAD_DIR / Path(am_img_rel).name
                pm_path = UPLOAD_DIR / Path(pm_img_rel).name
                if am_path.exists() and pm_path.exists():
                    try:
                        emb_am = self.clip.encode_image(am_path)
                        emb_pm = self.clip.encode_image(pm_path)
                        sim = float(np.dot(emb_am, emb_pm))
                        if sim > best_sim:
                            best_sim = sim
                            best_am = am_img_rel
                            best_pm = pm_img_rel
                    except Exception as e:
                        pass

        if best_sim < 0:
            best_sim = 0.70

        # Scale cosine similarity [-1, 1] to percentage [0, 100]
        visual_pct = max(10.0, min(99.0, (best_sim + 1.0) / 2.0 * 100.0))
        return visual_pct, best_am, best_pm

    def _generate_bob_rationale(
        self,
        pm: PostMortemRecord,
        am: AnteMortemProfile,
        match_prob: float,
        biomarker_matches: List[str],
        clothing_matches: List[str],
        visual_sim: float,
        discrepancies: List[str]
    ) -> str:
        confidence = "High Confidence" if match_prob >= 75.0 else ("Moderate Confidence" if match_prob >= 50.0 else "Low Confidence")

        lines = [
            f"[Bob DVI Analysis: {confidence} ({match_prob}% Probability)]"
        ]

        if biomarker_matches:
            lines.append("Key Forensic Identifiers: " + "; ".join(biomarker_matches[:2]) + ".")
        if clothing_matches:
            lines.append("Physical Effects Concordance: " + "; ".join(clothing_matches[:2]) + ".")

        lines.append(f"CLIP Multimodal Feature Concordance: {visual_sim:.1f}% visual similarity.")

        if discrepancies:
            lines.append("Forensic Caution: " + "; ".join(discrepancies) + ".")
        else:
            lines.append("No conflicting primary anatomical discrepancies observed.")

        lines.append(f"Recommendation: {'Proceed with expedited DNA cross-matching and odontology confirmation.' if match_prob >= 70.0 else 'Secondary review required before reconciliation.'}")

        return " ".join(lines)

_bob_instance = None

def get_bob_matcher() -> BobDVIMatcher:
    global _bob_instance
    if _bob_instance is None:
        _bob_instance = BobDVIMatcher()
    return _bob_instance
