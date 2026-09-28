import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image
from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL, BASE_DIR, UPLOAD_DIR, ENV_FILE

FORENSIC_PROMPT = """You are a senior forensic identification specialist analyzing evidence photos for a Disaster Victim Identification (DVI) Post-Mortem Registry.
Examine all provided photos with high forensic accuracy and extract all visible identifying characteristics:

1. Garments & Clothing: specific types (e.g. polo shirt, round-neck t-shirt, ethnic kurta, trousers, denim jeans), colors, fabric texture, prints, brand labels if visible.
2. Belongings & Accessories: wristwatches (dial, strap type), rings, sacred threads (kalawa), metal bangles (kada), chains/necklaces, amulets, belts, footwear.
3. Anatomical Markers & Biological Cues: surgical or injury scars (location and appearance), tattoos (subject matter, location), moles, birthmarks, hair color/length, facial stubble/beard, clean-shaven, biological sex cues (Male/Female).
4. Dominant Colors: prominent color palette observed with names and approximate hex codes.
5. Overall Forensic Summary: a clear, concise professional summary synthesized from all images.

Respond strictly in valid JSON matching this schema:
{
  "detected_clothing": [{"name": string, "confidence": number, "details": string}],
  "detected_accessories": [{"name": string, "confidence": number, "details": string}],
  "detected_marks": [{"name": string, "confidence": number, "details": string}],
  "detected_colors": [{"name": string, "hex": string}],
  "suggested_gender": "Male" | "Female" | "Unknown",
  "summary": string,
  "per_image": [{"image_index": number, "key_observations": string}]
}
"""

class GeminiFeatureExtractor:
    _instance = None

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "") or GEMINI_API_KEY
        self.model_name = os.getenv("GEMINI_MODEL", "") or GEMINI_MODEL or "gemini-3.1-flash-lite"
        self._init_client()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_client(self):
        if self.api_key and self.api_key.strip():
            try:
                self.client = genai.Client(api_key=self.api_key.strip())
            except Exception as e:
                print(f"Error initializing Gemini client: {e}")
                self.client = None
        else:
            self.client = None

    def is_configured(self) -> bool:
        return bool(self.client and self.api_key and len(self.api_key.strip()) > 10)

    def set_api_key(self, api_key: str, model_name: Optional[str] = None):
        clean_key = api_key.strip()
        self.api_key = clean_key
        if model_name and model_name.strip():
            self.model_name = model_name.strip()
        self._init_client()

        # Persist to .env
        try:
            env_lines = []
            key_set = False
            model_set = False
            if ENV_FILE.exists():
                with open(ENV_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            env_lines.append(f"GEMINI_API_KEY={clean_key}\n")
                            key_set = True
                        elif line.startswith("GEMINI_MODEL="):
                            env_lines.append(f"GEMINI_MODEL={self.model_name}\n")
                            model_set = True
                        else:
                            env_lines.append(line)
            if not key_set:
                env_lines.append(f"GEMINI_API_KEY={clean_key}\n")
            if not model_set:
                env_lines.append(f"GEMINI_MODEL={self.model_name}\n")

            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.writelines(env_lines)
            os.environ["GEMINI_API_KEY"] = clean_key
            os.environ["GEMINI_MODEL"] = self.model_name
        except Exception as e:
            print(f"Warning saving API key to .env: {e}")

    def extract_features(self, image_paths: List[str]) -> Dict[str, Any]:
        """
        Sends all evidence photos to Google Gemini multimodal model
        and extracts comprehensive, accurate forensic features.
        """
        if not self.is_configured():
            return {
                "error": "Gemini API key is not configured.",
                "gemini_active": False,
                "summary": "Gemini API key required for multimodal feature extraction."
            }

        loaded_images = []
        for p in image_paths:
            resolved = p
            if isinstance(p, str) and p.startswith("/static/uploads/"):
                rel = p.replace("/static/uploads/", "")
                resolved = UPLOAD_DIR / rel

            path_obj = Path(resolved)
            if path_obj.exists():
                try:
                    img = Image.open(path_obj).convert("RGB")
                    # Resize if extremely large to save bandwidth while keeping sharp details
                    if max(img.size) > 1600:
                        img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                    loaded_images.append(img)
                except Exception as e:
                    print(f"Error opening image {resolved}: {e}")

        if not loaded_images:
            return {
                "error": "No valid images could be loaded for Gemini analysis.",
                "gemini_active": True,
                "summary": "No photos available for extraction."
            }

        contents = [FORENSIC_PROMPT] + loaded_images

        # Try designated model, with graceful fallback to other active models
        models_to_try = [
            self.model_name,
            "gemini-3.1-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-2.5-flash"
        ]
        models_to_try = list(dict.fromkeys([m for m in models_to_try if m]))

        last_error = None
        for model in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )

                if response and response.text:
                    parsed = json.loads(response.text)
                    # Normalize confidence to percentage 0-100
                    for category in ["detected_clothing", "detected_accessories", "detected_marks"]:
                        for item in parsed.get(category, []):
                            if isinstance(item, dict) and "confidence" in item:
                                val = item["confidence"]
                                if isinstance(val, (int, float)) and val <= 1.0:
                                    item["confidence"] = round(val * 100, 1)

                    parsed["engine"] = f"Gemini ({model})"
                    parsed["gemini_active"] = True
                    parsed["total_images_analyzed"] = len(loaded_images)
                    return parsed

            except Exception as e:
                last_error = str(e)
                print(f"Gemini model {model} attempt failed: {e}")

        return {
            "error": f"Gemini extraction failed: {last_error}",
            "gemini_active": True,
            "summary": "Gemini model error during image analysis."
        }


def get_gemini_extractor() -> GeminiFeatureExtractor:
    return GeminiFeatureExtractor.get_instance()
