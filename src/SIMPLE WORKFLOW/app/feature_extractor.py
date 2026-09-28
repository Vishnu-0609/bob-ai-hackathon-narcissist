import os
import io
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import numpy as np

from app.config import UPLOAD_DIR
from app.model import get_clip_model

# Candidate categories for zero-shot forensic extraction
CANDIDATE_CATEGORIES = {
    "clothing": [
        ("white shirt or top", "White Shirt / Top"),
        ("black shirt or t-shirt", "Black Shirt / Top"),
        ("blue shirt or blue clothing", "Blue Shirt / Clothing"),
        ("red or maroon shirt or kurta", "Maroon / Red Kurta"),
        ("ethnic kurta or traditional wear", "Ethnic Kurta / Dress"),
        ("blue denim or jeans", "Blue Jeans / Denim"),
        ("dark trousers or pants", "Dark Trousers"),
        ("jacket or coat or hoodie", "Jacket / Outerwear"),
        ("saree or traditional drape", "Saree / Traditional Drape"),
        ("shorts or casual wear", "Shorts / Casual Wear"),
        ("patterned or printed fabric", "Patterned Fabric"),
        ("plain solid color fabric", "Solid Color Fabric")
    ],
    "accessories": [
        ("wristwatch or watch on wrist", "Wristwatch"),
        ("finger ring or wedding band", "Finger Ring"),
        ("sacred thread or red kalawa on wrist", "Sacred Wrist Thread / Kalawa"),
        ("kada or circular metal bangle", "Kada / Metal Bangle"),
        ("necklace or gold ornamental chain", "Necklace / Chain"),
        ("earrings or ear studs", "Earrings"),
        ("leather belt or strap", "Belt / Strap"),
        ("shoes or leather footwear", "Footwear / Shoes")
    ],
    "marks": [
        ("visible surgical scar or incision mark", "Surgical Scar / Incision"),
        ("tattoo on skin or arm", "Tattoo Mark"),
        ("birthmark or pigmented mole", "Birthmark / Mole"),
        ("facial stubble or beard", "Facial Stubble / Beard"),
        ("clean shaven face", "Clean Shaven"),
        ("short black hair", "Short Black Hair"),
        ("long black hair", "Long Hair"),
        ("gray or silver hair", "Gray / Silver Hair")
    ],
    "gender": [
        ("male person or man", "Male"),
        ("female person or woman", "Female")
    ]
}

def rgb_to_color_name(r: int, g: int, b: int) -> Tuple[str, str]:
    """Map RGB to human-friendly color name and hex code."""
    hex_code = f"#{r:02x}{g:02x}{b:02x}"
    
    # Check grayscale / intensity
    if r > 215 and g > 215 and b > 215:
        return "White", hex_code
    if r < 40 and g < 40 and b < 40:
        return "Black", hex_code
    if abs(r - g) < 20 and abs(g - b) < 20 and abs(r - b) < 20:
        if r > 160:
            return "Light Gray", hex_code
        elif r > 90:
            return "Medium Gray", hex_code
        else:
            return "Dark Charcoal", hex_code

    # Chromatic colors
    if r > g + 40 and r > b + 40:
        if r > 150 and g < 80 and b < 80:
            return "Red / Crimson", hex_code
        if r < 140 and g < 60 and b < 60:
            return "Maroon / Burgundy", hex_code
        return "Reddish", hex_code

    if b > r + 30 and b > g + 30:
        if b < 100:
            return "Navy Blue", hex_code
        if b > 160 and r < 100 and g < 140:
            return "Bright Blue", hex_code
        return "Blue", hex_code

    if g > r + 30 and g > b + 30:
        if g < 110:
            return "Dark / Olive Green", hex_code
        return "Green", hex_code

    if r > 160 and g > 130 and b < 90:
        if r > 200 and g > 180:
            return "Yellow", hex_code
        return "Ochre / Khaki", hex_code

    if r > 120 and g > 70 and b < 60:
        return "Brown / Tan", hex_code

    if r > 160 and g < 110 and b > 140:
        return "Purple / Violet", hex_code

    if r > 180 and g > 100 and b < 70:
        return "Orange", hex_code

    return "Multi-tone", hex_code


def extract_color_palette(image: Image.Image, num_colors: int = 4) -> List[Dict[str, str]]:
    """Extract dominant color palette using fast octree quantization."""
    try:
        small = image.resize((80, 80))
        palette_img = small.quantize(colors=num_colors, method=Image.Quantize.FASTOCTREE)
        palette = palette_img.getpalette()[:num_colors * 3]
        
        seen_names = set()
        colors = []
        for i in range(0, len(palette), 3):
            r, g, b = palette[i], palette[i+1], palette[i+2]
            name, hex_code = rgb_to_color_name(r, g, b)
            if name not in seen_names:
                seen_names.add(name)
                colors.append({
                    "name": name,
                    "hex": hex_code,
                    "rgb": f"rgb({r},{g},{b})"
                })
        return colors
    except Exception as e:
        print(f"Error in color extraction: {e}")
        return []


class MultiImageFeatureExtractor:
    _instance = None

    def __init__(self):
        self.clip = get_clip_model()
        self._precompute_text_embeddings()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _precompute_text_embeddings(self):
        """Precomputes normalized CLIP text embeddings for candidate tags."""
        self.text_labels = {}
        self.text_vectors = {}

        for category, items in CANDIDATE_CATEGORIES.items():
            prompts = [f"a clear forensic photo of {desc}" for desc, _ in items]
            display_names = [name for _, name in items]
            
            vecs = []
            for p in prompts:
                vec = self.clip.encode_text(p)
                vecs.append(vec)

            self.text_labels[category] = display_names
            self.text_vectors[category] = np.array(vecs)  # shape: [N, 512]

    def analyze_single_image(self, image_path_or_obj) -> Dict[str, Any]:
        """Analyzes a single image for clothing, accessories, marks, gender cues, and color palette."""
        try:
            if isinstance(image_path_or_obj, (str, Path)):
                img = Image.open(image_path_or_obj).convert("RGB")
            else:
                img = image_path_or_obj.convert("RGB")
        except Exception as e:
            return {"error": f"Failed to load image: {e}"}

        # 1. Dominant colors
        color_palette = extract_color_palette(img, num_colors=4)

        # 2. CLIP image embedding
        img_vec = np.array(self.clip.encode_image(img))  # shape: [512]

        results = {
            "clothing": [],
            "accessories": [],
            "marks": [],
            "gender_scores": {},
            "color_palette": color_palette,
            "top_features": []
        }

        # Check each category
        for category, text_matrix in self.text_vectors.items():
            labels = self.text_labels[category]
            # Dot product with pre-normalized vectors = cosine similarity
            sims = text_matrix @ img_vec

            for label, score in zip(labels, sims.tolist()):
                if category == "gender":
                    results["gender_scores"][label] = round(score, 4)
                else:
                    # Threshold for detection
                    if score >= 0.225:
                        results[category].append({
                            "feature": label,
                            "confidence": round(score * 100, 1)
                        })
                        results["top_features"].append({
                            "category": category,
                            "feature": label,
                            "score": round(score, 4)
                        })

        # Sort detections by confidence
        for cat in ["clothing", "accessories", "marks"]:
            results[cat].sort(key=lambda x: x["confidence"], reverse=True)

        results["top_features"].sort(key=lambda x: x["score"], reverse=True)
        return results

    def extract_from_multiple_images(self, image_paths: List[str]) -> Dict[str, Any]:
        """
        Extracts and aggregates features across ALL uploaded images for a post-mortem record.
        Prioritizes Google Gemini multimodal vision when API key is configured.
        """
        if not image_paths:
            return {
                "detected_clothing": [],
                "detected_accessories": [],
                "detected_marks": [],
                "detected_colors": [],
                "suggested_gender": "Unknown",
                "summary": "No images provided for visual feature extraction.",
                "per_image": [],
                "gemini_active": False
            }

        # 1. Check if Gemini is configured and active
        from app.gemini_extractor import get_gemini_extractor
        gemini = get_gemini_extractor()
        if gemini.is_configured():
            gemini_result = gemini.extract_features(image_paths)
            if not gemini_result.get("error"):
                return gemini_result
            else:
                print(f"Gemini notice: {gemini_result.get('error')}. Falling back to local CLIP extractor.")

        aggregated_clothing = {}
        aggregated_accessories = {}
        aggregated_marks = {}
        aggregated_colors = {}
        gender_votes = {"Male": 0.0, "Female": 0.0}
        per_image_results = []

        for idx, img_ref in enumerate(image_paths):
            # Resolve path
            resolved_path = img_ref
            if img_ref.startswith("/static/uploads/"):
                rel = img_ref.replace("/static/uploads/", "")
                resolved_path = UPLOAD_DIR / rel

            if not Path(resolved_path).exists():
                continue

            analysis = self.analyze_single_image(resolved_path)
            if "error" in analysis:
                continue

            per_image_results.append({
                "image_index": idx + 1,
                "image_path": img_ref,
                "clothing": [c["feature"] for c in analysis.get("clothing", [])[:3]],
                "accessories": [a["feature"] for a in analysis.get("accessories", [])[:3]],
                "marks": [m["feature"] for m in analysis.get("marks", [])[:2]],
                "colors": [col["name"] for col in analysis.get("color_palette", [])[:3]]
            })

            # Aggregate clothing
            for item in analysis.get("clothing", []):
                feat = item["feature"]
                aggregated_clothing[feat] = max(aggregated_clothing.get(feat, 0), item["confidence"])

            # Aggregate accessories
            for item in analysis.get("accessories", []):
                feat = item["feature"]
                aggregated_accessories[feat] = max(aggregated_accessories.get(feat, 0), item["confidence"])

            # Aggregate marks
            for item in analysis.get("marks", []):
                feat = item["feature"]
                aggregated_marks[feat] = max(aggregated_marks.get(feat, 0), item["confidence"])

            # Aggregate colors
            for col in analysis.get("color_palette", []):
                cname = col["name"]
                if cname not in aggregated_colors:
                    aggregated_colors[cname] = col

            # Gender votes
            g_scores = analysis.get("gender_scores", {})
            gender_votes["Male"] += g_scores.get("Male", 0.0)
            gender_votes["Female"] += g_scores.get("Female", 0.0)

        # Build sorted list of detected features
        clothing_list = [
            {"name": k, "confidence": v}
            for k, v in sorted(aggregated_clothing.items(), key=lambda x: x[1], reverse=True)
        ]
        accessories_list = [
            {"name": k, "confidence": v}
            for k, v in sorted(aggregated_accessories.items(), key=lambda x: x[1], reverse=True)
        ]
        marks_list = [
            {"name": k, "confidence": v}
            for k, v in sorted(aggregated_marks.items(), key=lambda x: x[1], reverse=True)
        ]
        colors_list = list(aggregated_colors.values())

        # Determine suggested gender
        suggested_gender = "Unknown"
        if gender_votes["Male"] > 0 or gender_votes["Female"] > 0:
            diff = gender_votes["Male"] - gender_votes["Female"]
            if diff > 0.04:
                suggested_gender = "Male"
            elif diff < -0.04:
                suggested_gender = "Female"

        # Generate descriptive forensic summary
        summary_sentences = []
        if clothing_list:
            top_clothes = ", ".join([c["name"] for c in clothing_list[:3]])
            summary_sentences.append(f"Clothing detected: {top_clothes}.")
        if colors_list:
            top_colors = ", ".join([c["name"] for c in colors_list[:3]])
            summary_sentences.append(f"Dominant colors: {top_colors}.")
        if accessories_list:
            top_acc = ", ".join([a["name"] for a in accessories_list[:3]])
            summary_sentences.append(f"Belongings / accessories: {top_acc}.")
        if marks_list:
            top_m = ", ".join([m["name"] for m in marks_list[:2]])
            summary_sentences.append(f"Anatomical features / marks: {top_m}.")
        if suggested_gender != "Unknown":
            summary_sentences.append(f"Estimated visual presentation: {suggested_gender}.")

        final_summary = " ".join(summary_sentences) if summary_sentences else "Visual feature extraction completed with no distinct high-confidence tags."

        return {
            "total_images_analyzed": len(per_image_results),
            "detected_clothing": clothing_list,
            "detected_accessories": accessories_list,
            "detected_marks": marks_list,
            "detected_colors": colors_list,
            "suggested_gender": suggested_gender,
            "summary": final_summary,
            "per_image": per_image_results,
            "gemini_active": False,
            "engine": "CLIP Local Fallback"
        }


def get_feature_extractor() -> MultiImageFeatureExtractor:
    return MultiImageFeatureExtractor.get_instance()
