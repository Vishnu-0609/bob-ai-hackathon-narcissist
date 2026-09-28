import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "DVI-Bridge"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # IBM Bob Integration
    BOB_API_KEY: str = ""
    BOB_API_URL: str = "https://api.bob.ibm.com/v1"
    BOB_TIMEOUT_SECONDS: float = 30.0

    # Database
    DATABASE_URL: str = "sqlite:///./dvi.db"

    # Security & JWT
    JWT_SECRET: str = "dvi_super_secret_jwt_key_bob_hackathon_2026_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    # Matching Engine Configurable Default Weights (Total = 100)
    WEIGHT_SEX: float = 10.0
    WEIGHT_AGE: float = 10.0
    WEIGHT_HEIGHT: float = 8.0
    WEIGHT_BLOOD_GROUP: float = 7.0
    WEIGHT_SCARS: float = 15.0
    WEIGHT_BIRTHMARKS: float = 10.0
    WEIGHT_TATTOOS: float = 8.0
    WEIGHT_CLOTHING: float = 5.0
    WEIGHT_JEWELLERY: float = 5.0
    WEIGHT_DENTAL: float = 12.0
    WEIGHT_MEDICAL_IMPLANTS: float = 5.0
    WEIGHT_LOCATION_TIME: float = 5.0

    # Matching Thresholds
    STRONG_CANDIDATE_THRESHOLD: float = 80.0
    MODERATE_CANDIDATE_THRESHOLD: float = 50.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
