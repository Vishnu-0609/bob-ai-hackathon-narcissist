import os
import uuid
from typing import Optional, Tuple
from pathlib import Path
from app.core.config import settings


class ImageStorageService:
    """
    Abstracted image storage manager for secure, UUID-based file persistence.
    Supports easy future swapping with S3/GCS object stores.
    """

    @classmethod
    def get_base_dir(cls) -> Path:
        # Base dir relative to backend root
        base = Path(__file__).resolve().parent.parent.parent.parent / settings.IMAGE_STORAGE_DIR
        base.mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def get_storage_subdir(cls, entity_type: str = "AM") -> Path:
        sub = "am" if (entity_type or "").upper().startswith("AM") else ("pm" if (entity_type or "").upper().startswith("PM") else "other")
        target_dir = cls.get_base_dir() / sub
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    @classmethod
    def save_image(
        cls,
        file_bytes: bytes,
        image_id: str,
        entity_type: str = "AM",
        extension: str = ".jpg",
    ) -> str:
        """
        Saves raw validated bytes using a random UUID filename in private directory.
        Returns relative storage path.
        """
        if not extension.startswith("."):
            extension = f".{extension}"
        
        # Ensure clean standard extension
        ext = extension.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"

        target_dir = cls.get_storage_subdir(entity_type)
        storage_filename = f"{image_id}{ext}"
        full_path = target_dir / storage_filename

        with open(full_path, "wb") as f:
            f.write(file_bytes)

        # Return storage path relative to storage root
        sub = "am" if (entity_type or "").upper().startswith("AM") else ("pm" if (entity_type or "").upper().startswith("PM") else "other")
        return f"{sub}/{storage_filename}"

    @classmethod
    def get_absolute_path(cls, storage_path: str) -> Path:
        """
        Resolves relative storage path safely against base directory preventing traversal.
        """
        base = cls.get_base_dir()
        resolved = (base / storage_path).resolve()
        # Security check: ensure path is inside base
        if not str(resolved).startswith(str(base)):
            raise ValueError("Invalid storage path: directory traversal detected.")
        return resolved

    @classmethod
    def read_image_bytes(cls, storage_path: str) -> bytes:
        """
        Reads raw image bytes from storage.
        """
        path = cls.get_absolute_path(storage_path)
        if not path.exists():
            raise FileNotFoundError(f"Stored image file not found: {storage_path}")
        with open(path, "rb") as f:
            return f.read()

    @classmethod
    def delete_image(cls, storage_path: str) -> bool:
        """
        Deletes image file from storage if present.
        """
        try:
            path = cls.get_absolute_path(storage_path)
            if path.exists():
                path.unlink()
                return True
        except Exception:
            pass
        return False
