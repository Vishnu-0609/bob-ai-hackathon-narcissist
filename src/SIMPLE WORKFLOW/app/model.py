from typing import List, Union
from pathlib import Path
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
from app.config import CLIP_MODEL_NAME, DEVICE

class CLIPEmbeddingModel:
    _instance = None

    def __init__(self):
        print(f"Loading CLIP model '{CLIP_MODEL_NAME}' on {DEVICE}...")
        self.device = DEVICE
        self.model = CLIPModel.from_pretrained(CLIP_MODEL_NAME).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
        self.model.eval()
        print("CLIP model loaded successfully.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _extract_tensor(self, outputs) -> torch.Tensor:
        if isinstance(outputs, torch.Tensor):
            return outputs
        if hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
            return outputs.pooler_output
        if hasattr(outputs, "text_embeds") and outputs.text_embeds is not None:
            return outputs.text_embeds
        if hasattr(outputs, "image_embeds") and outputs.image_embeds is not None:
            return outputs.image_embeds
        return outputs[0]

    def encode_image(self, image_input: Union[Image.Image, str, Path]) -> List[float]:
        """Generate normalized 512-d CLIP embedding for an image."""
        if isinstance(image_input, (str, Path)):
            image = Image.open(image_input).convert("RGB")
        else:
            image = image_input.convert("RGB")

        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)
            features = self._extract_tensor(outputs)
            # L2 normalization for cosine similarity
            features = features / features.norm(p=2, dim=-1, keepdim=True)
            embedding = features.squeeze(0).cpu().numpy().tolist()
        return embedding

    def encode_text(self, text: str) -> List[float]:
        """Generate normalized 512-d CLIP embedding for a text query/description."""
        inputs = self.processor(text=[text], return_tensors="pt", padding=True, truncation=True).to(self.device)
        with torch.no_grad():
            outputs = self.model.get_text_features(**inputs)
            features = self._extract_tensor(outputs)
            # L2 normalization for cosine similarity
            features = features / features.norm(p=2, dim=-1, keepdim=True)
            embedding = features.squeeze(0).cpu().numpy().tolist()
        return embedding

def get_clip_model() -> CLIPEmbeddingModel:
    return CLIPEmbeddingModel.get_instance()
