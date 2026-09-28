import os
import time
import json
import logging
from typing import Optional, Dict, Any
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import settings
from app.services.vision.extraction_schema import ImageExtraction
from app.services.vision.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    AM_EXTRACTION_PROMPT,
    PM_EXTRACTION_PROMPT,
)

logger = logging.getLogger("dvi.vision.gemini")


class GeminiVisionError(Exception):
    """Base exception for Gemini Vision errors."""
    def __init__(self, message: str, status_code: int = 500, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retryable = retryable


class GeminiRateLimitError(GeminiVisionError):
    """Raised on 429 Too Many Requests."""
    def __init__(self, message: str = "Gemini API rate limit exceeded."):
        super().__init__(message, status_code=429, retryable=True)


class GeminiClient:
    """
    Official Google Gemini API client for multimodal evidence extraction.
    Ensures safe handling of API credentials, structured JSON extraction,
    retries with exponential backoff, and robust fallback handling.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = settings.GEMINI_MAX_RETRIES,
        timeout_seconds: float = settings.GEMINI_TIMEOUT_SECONDS,
    ):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.model = model or settings.GEMINI_MODEL or "gemini-3.1-flash-lite"
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

        self._client: Optional[genai.Client] = None
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize Gemini Client: %s", type(e).__name__)
                self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self._client)

    def extract_image_evidence(
        self,
        image_bytes: bytes,
        mime_type: str,
        record_type: str = "AM",
        image_type: str = "PORTRAIT",
    ) -> Dict[str, Any]:
        """
        Invokes Gemini 2.5 Flash to extract structured observable forensic evidence.
        Applies exponential backoff retries for rate limits (429) and transient server errors (5xx).
        """
        if not self.is_configured:
            logger.info("Gemini API key not configured or client uninitialized. Using mock extraction fallback.")
            return self._generate_mock_extraction(record_type, image_type)

        prompt_template = AM_EXTRACTION_PROMPT if record_type.upper() == "AM" else PM_EXTRACTION_PROMPT
        user_prompt = prompt_template.format(image_type=image_type)

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        config = types.GenerateContentConfig(
            system_instruction=EXTRACTION_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ImageExtraction,
            temperature=0.1,
        )

        # Candidates ordered by preference
        candidate_models = [self.model]
        for fallback in ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_exception = None

        for model_name in candidate_models:
            delay = 1.0
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(
                        "Invoking Gemini Vision (model=%s, record_type=%s, attempt=%d/%d)",
                        model_name,
                        record_type,
                        attempt,
                        self.max_retries,
                    )

                    response = self._client.models.generate_content(
                        model=model_name,
                        contents=[image_part, user_prompt],
                        config=config,
                    )

                    if not response or not response.text:
                        raise GeminiVisionError("Empty response received from Gemini API.")

                    raw_json = response.text.strip()
                    if raw_json.startswith("```"):
                        lines = raw_json.split("\n")
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].strip() == "```":
                            lines = lines[:-1]
                        raw_json = "\n".join(lines).strip()

                    parsed_dict = json.loads(raw_json)
                    validated = ImageExtraction.model_validate(parsed_dict)
                    result_data = validated.model_dump()
                    result_data["record_type"] = record_type.upper()
                    result_data["image_type"] = image_type.upper()
                    self.model = model_name  # Record successful model
                    return result_data

                except APIError as api_err:
                    last_exception = api_err
                    code = getattr(api_err, "code", 500)
                    message = getattr(api_err, "message", str(api_err))

                    # If model is not found or deprecated, try next model immediately
                    if code == 404 or "is no longer available" in message:
                        logger.warning("Gemini model %s unavailable (%d: %s). Trying next candidate.", model_name, code, message)
                        break

                    if code == 429:
                        logger.warning("Gemini 429 Rate Limit on %s (attempt %d): %s", model_name, attempt, message)
                        if attempt < self.max_retries:
                            time.sleep(delay)
                            delay *= 2
                            continue
                        # If rate limited on this model, try next model
                        break
                    elif code >= 500:
                        logger.warning("Gemini %d Server Error on %s (attempt %d): %s", code, model_name, attempt, message)
                        if attempt < self.max_retries:
                            time.sleep(delay)
                            delay *= 2
                            continue
                        break
                    else:
                        logger.error("Gemini Client Error (%d): %s", code, message)
                        raise GeminiVisionError(f"Gemini API error ({code}): {message}", status_code=code, retryable=False)

                except json.JSONDecodeError as json_err:
                    logger.error("Failed to parse structured JSON from Gemini output: %s", json_err)
                    raise GeminiVisionError(f"Malformed JSON returned by Gemini Vision: {str(json_err)}")

                except Exception as exc:
                    last_exception = exc
                    logger.warning("Error during Gemini call (%s, attempt %d): %s", model_name, attempt, exc)
                    if attempt < self.max_retries:
                        time.sleep(delay)
                        delay *= 2
                        continue
                    break

        raise GeminiVisionError(f"Gemini Vision extraction failed across all model endpoints: {str(last_exception)}")

    def _generate_mock_extraction(self, record_type: str, image_type: str) -> Dict[str, Any]:
        """
        Deterministic mock extraction for development, testing, and offline fallback mode.
        """
        is_am = record_type.upper() == "AM"
        return {
            "record_type": "AM" if is_am else "PM",
            "image_type": image_type.upper(),
            "observations": {
                "clothing": [
                    {
                        "item_type": "shirt",
                        "color": "blue",
                        "pattern": "solid",
                        "description": "blue collared shirt",
                        "status": "OBSERVED",
                        "confidence": 0.94,
                        "notes": "Clearly visible in upper torso region",
                    },
                    {
                        "item_type": "jeans",
                        "color": "dark blue",
                        "pattern": "denim",
                        "description": "dark denim jeans",
                        "status": "OBSERVED",
                        "confidence": 0.88,
                        "notes": "Visible lower garment",
                    },
                ],
                "jewellery": [
                    {
                        "item_type": "ring",
                        "material_or_color": "silver-colored",
                        "location": "right hand finger",
                        "description": "silver-colored metallic ring band",
                        "status": "OBSERVED",
                        "confidence": 0.86,
                        "notes": "Visible on digit",
                    }
                ],
                "tattoos": [
                    {
                        "description": "bird-like tattoo in flight with spread wings",
                        "location": "right shoulder",
                        "design_motifs": ["bird", "wings", "flight"],
                        "colors": ["dark ink"],
                        "status": "OBSERVED",
                        "confidence": 0.82,
                        "notes": "Distinctive avian motif on deltoid area",
                    }
                ],
                "scars_or_marks": [
                    {
                        "description": "linear surgical mark approximately 3 cm",
                        "location": "left forearm",
                        "mark_type": "scar",
                        "status": "OBSERVED",
                        "confidence": 0.78,
                        "notes": "Visible on dorsal/volar aspect of left forearm",
                    }
                ],
                "physical_characteristics": [
                    {
                        "attribute": "apparent_build",
                        "value": "medium build",
                        "status": "OBSERVED",
                        "confidence": 0.85,
                    },
                    {
                        "attribute": "hair_color",
                        "value": "dark brown / black",
                        "status": "OBSERVED",
                        "confidence": 0.90,
                    },
                ],
                "visible_text": [],
                "other_observations": [
                    "Visual observation documented under standard forensic imaging protocol"
                ],
            },
            "image_quality": {
                "status": "GOOD",
                "occlusion": False,
                "occlusion_details": None,
                "lighting": "ADEQUATE",
                "resolution_assessment": "SUFFICIENT",
            },
            "summary": "Visual analysis identified a blue shirt, silver-colored ring, bird-like tattoo on the right shoulder, and a linear mark on the left forearm.",
        }
