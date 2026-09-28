import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.schemas import AMExtractionOutput, PMExtractionOutput
from app.services.bob_client import bob_client


class BobExtractionService:
    @staticmethod
    def _local_extract_am(text: str) -> Dict[str, Any]:
        """
        Deterministic NLP extractor for family free-text narratives when Bob is offline or in local demo mode.
        """
        lower = text.lower()
        extracted: Dict[str, Any] = {
            "name": None,
            "age": None,
            "sex": None,
            "height_cm": None,
            "weight_kg": None,
            "blood_group": None,
            "physical_description": text,
            "scars": [],
            "birthmarks": [],
            "tattoos": [],
            "clothing": [],
            "jewellery": [],
            "dental_notes": None,
            "medical_history": None,
            "implants": [],
            "last_seen_location": None,
            "last_seen_time": None,
        }

        # Age detection
        age_match = re.search(r"\b(?:age[d\s:]+|around|about|is\s+)?(\d{1,2})\s*(?:years|yrs|yo|yr old)?\b", lower)
        if age_match:
            try:
                extracted["age"] = int(age_match.group(1))
            except Exception:
                pass

        # Sex detection
        if any(w in lower for w in ["brother", "husband", "son", "father", "male", "man", "he ", "his "]):
            extracted["sex"] = "MALE"
        elif any(w in lower for w in ["sister", "wife", "daughter", "mother", "female", "woman", "she ", "her "]):
            extracted["sex"] = "FEMALE"

        # Height detection (cm or ft/inches)
        cm_match = re.search(r"(\d{2,3})\s*(?:cm|centimeters)", lower)
        ft_match = re.search(r"(\d)['’](\d{1,2})?|(\d)\s*(?:feet|ft)\s*(\d{1,2})?\s*(?:in|inches)?", lower)
        if cm_match:
            extracted["height_cm"] = float(cm_match.group(1))
        elif ft_match:
            ft = int(ft_match.group(1) or ft_match.group(3) or 5)
            inch = int(ft_match.group(2) or ft_match.group(4) or 0)
            extracted["height_cm"] = round((ft * 12 + inch) * 2.54, 1)

        # Blood Group
        bg_match = re.search(r"\b(a|b|ab|o)\s*([+-]|positive|negative)\b", lower)
        if bg_match:
            g = bg_match.group(1).upper()
            sign = "+" if "+" in bg_match.group(2) or "pos" in bg_match.group(2) else "-"
            extracted["blood_group"] = f"{g}{sign}"

        # Scars
        for match in re.finditer(r"(?:scar|burn\s*mark|stitch(?:es)?)\s*(?:on|near|across|at)?\s*([a-z\s]{3,30})", lower):
            loc = match.group(1).strip()
            extracted["scars"].append({"location": loc, "description": match.group(0).strip()})

        # Tattoos
        for match in re.finditer(r"tattoo\s*(?:of\s+([a-z\s]{3,20}))?\s*(?:on|at|near)?\s*([a-z\s]{3,30})", lower):
            desc = match.group(1) or "tattoo"
            loc = match.group(2) or "body"
            extracted["tattoos"].append({"description": desc.strip(), "location": loc.strip()})

        # Birthmarks
        for match in re.finditer(r"(?:birthmark|mole)\s*(?:on|at|near)?\s*([a-z\s]{3,30})", lower):
            extracted["birthmarks"].append({"location": match.group(1).strip(), "description": match.group(0).strip()})

        # Clothing
        clothing_keywords = ["shirt", "t-shirt", "tshirt", "jeans", "pants", "saree", "kurta", "jacket", "dress", "shorts", "shoes"]
        for word in clothing_keywords:
            color_match = re.search(rf"\b([a-z]+)\s+{word}\b", lower)
            if color_match:
                extracted["clothing"].append(f"{color_match.group(1)} {word}")
            elif word in lower:
                extracted["clothing"].append(word)

        # Jewellery
        jewellery_keywords = ["ring", "watch", "chain", "bracelet", "necklace", "bangle", "earring", "silver ring", "gold ring"]
        for j in jewellery_keywords:
            if j in lower:
                extracted["jewellery"].append(j)

        # Dental notes
        if "dental" in lower or "tooth" in lower or "crown" in lower or "filling" in lower or "denture" in lower:
            extracted["dental_notes"] = text

        # Medical history
        if "surgery" in lower or "fracture" in lower or "pacemaker" in lower or "implant" in lower:
            extracted["medical_history"] = text

        return extracted

    @staticmethod
    def _local_extract_pm(text: str) -> Dict[str, Any]:
        """
        Deterministic NLP extractor for post-mortem examiner field notes.
        """
        lower = text.lower()
        extracted: Dict[str, Any] = {
            "estimated_age_min": None,
            "estimated_age_max": None,
            "sex": None,
            "height_cm": None,
            "weight_kg": None,
            "blood_group": None,
            "physical_description": text,
            "scars": [],
            "birthmarks": [],
            "tattoos": [],
            "clothing": [],
            "jewellery": [],
            "dental_findings": None,
            "medical_findings": None,
            "implants": [],
            "recovery_location": None,
            "examiner": "Field Forensic Examiner",
        }

        # Age range
        range_match = re.search(r"(\d{1,2})\s*[-–to]+\s*(\d{1,2})\s*(?:years|yrs)?", lower)
        if range_match:
            extracted["estimated_age_min"] = int(range_match.group(1))
            extracted["estimated_age_max"] = int(range_match.group(2))
        else:
            single_match = re.search(r"(?:approx|approximately|around)?\s*(\d{1,2})\s*(?:years|yrs)", lower)
            if single_match:
                val = int(single_match.group(1))
                extracted["estimated_age_min"] = max(0, val - 3)
                extracted["estimated_age_max"] = val + 3

        # Sex
        if "male" in lower and "female" not in lower:
            extracted["sex"] = "MALE"
        elif "female" in lower:
            extracted["sex"] = "FEMALE"

        # Height
        cm_match = re.search(r"(\d{2,3})\s*(?:cm|centimeters)", lower)
        if cm_match:
            extracted["height_cm"] = float(cm_match.group(1))

        # Blood group
        bg_match = re.search(r"\b(a|b|ab|o)\s*([+-]|positive|negative)\b", lower)
        if bg_match:
            g = bg_match.group(1).upper()
            sign = "+" if "+" in bg_match.group(2) or "pos" in bg_match.group(2) else "-"
            extracted["blood_group"] = f"{g}{sign}"

        # Scars
        for match in re.finditer(r"(?:scar|healed\s*scar|surgical\s*scar)\s*(?:on|at|near|across)?\s*([a-z\s]{3,30})", lower):
            extracted["scars"].append({"location": match.group(1).strip(), "description": match.group(0).strip()})

        # Tattoos
        for match in re.finditer(r"tattoo\s*(?:of\s+([a-z\s]{3,20}))?\s*(?:on|at|near)?\s*([a-z\s]{3,30})", lower):
            desc = match.group(1) or "tattoo"
            loc = match.group(2) or "body"
            extracted["tattoos"].append({"description": desc.strip(), "location": loc.strip()})

        # Clothing
        clothing_keywords = ["shirt", "t-shirt", "tshirt", "jeans", "pants", "saree", "kurta", "jacket", "dress", "shorts", "shoes"]
        for word in clothing_keywords:
            color_match = re.search(rf"\b([a-z]+)\s+{word}\b", lower)
            if color_match:
                extracted["clothing"].append(f"{color_match.group(1)} {word}")
            elif word in lower:
                extracted["clothing"].append(word)

        # Jewellery
        jewellery_keywords = ["ring", "watch", "chain", "bracelet", "necklace", "bangle", "earring", "silver ring", "gold ring"]
        for j in jewellery_keywords:
            if j in lower:
                extracted["jewellery"].append(j)

        if "dental" in lower or "teeth" in lower or "molar" in lower or "filling" in lower:
            extracted["dental_findings"] = text

        if "implant" in lower or "prosthetic" in lower or "fracture" in lower or "surgical" in lower:
            extracted["medical_findings"] = text

        return extracted

    @staticmethod
    async def extract_am_profile(text: str, incident_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Coordinates AM structured extraction via IBM Bob agent with validation and local fallback.
        """
        prompt = (
            "You are Bob, a forensic data assistant helping families report missing persons after a disaster.\n\n"
            "Read the following narrative carefully and extract all forensic identifiers into a structured JSON object. "
            "Pull out physical details like age, sex, height, blood group, scars, tattoos, birthmarks, "
            "clothing last worn, jewellery, dental notes, medical implants, and last known location/time.\n\n"
            "Be thorough — even partial or approximate values are useful. "
            "If a field isn't mentioned, leave it null. Do not guess or infer beyond what's written.\n\n"
            f"Narrative:\n{text}"
        )
        api_result = await bob_client.call_bob_api(
            agent_name="AM_EXTRACTION",
            payload={"incident_id": incident_id, "text": text, "instruction": prompt},
            db=db,
        )

        if api_result.get("success") and "data" in api_result:
            try:
                validated = AMExtractionOutput.model_validate(api_result["data"]).model_dump()
                return {
                    "source": "IBM_BOB_AGENT",
                    "data": validated,
                    "raw_text": text,
                    "review_required": True,
                }
            except Exception:
                pass

        # Fallback to local heuristic extractor
        local_data = BobExtractionService._local_extract_am(text)
        return {
            "source": "DVI_LOCAL_EXTRACTOR",
            "data": local_data,
            "raw_text": text,
            "review_required": True,
        }

    @staticmethod
    async def extract_pm_profile(text: str, incident_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Coordinates PM structured extraction via IBM Bob agent with validation and local fallback.
        """
        prompt = (
            "You are Bob, a forensic data assistant helping DVI examiners log post-mortem findings after a disaster.\n\n"
            "Read the following examiner notes carefully and extract all observable forensic identifiers into a structured JSON object. "
            "Focus on: estimated age range, sex, height, weight, blood group, scars, tattoos, birthmarks, "
            "clothing and jewellery found on the body, dental findings, medical implants, recovery location, and examiner name.\n\n"
            "Use ranges where exact values aren't known (e.g. estimated_age_min / estimated_age_max). "
            "If a field is not mentioned, leave it null. Do not infer identity, ethnicity, cause of death, or exact age.\n\n"
            f"Examiner notes:\n{text}"
        )
        api_result = await bob_client.call_bob_api(
            agent_name="PM_EXTRACTION",
            payload={"incident_id": incident_id, "text": text, "instruction": prompt},
            db=db,
        )

        if api_result.get("success") and "data" in api_result:
            try:
                validated = PMExtractionOutput.model_validate(api_result["data"]).model_dump()
                return {
                    "source": "IBM_BOB_AGENT",
                    "data": validated,
                    "raw_text": text,
                    "review_required": True,
                }
            except Exception:
                pass

        local_data = BobExtractionService._local_extract_pm(text)
        return {
            "source": "DVI_LOCAL_EXTRACTOR",
            "data": local_data,
            "raw_text": text,
            "review_required": True,
        }
