"""
Konfigurationsmodul für das Selflearn Transkriptions-Backend

Dieses Modul zentralisiert alle Konfigurationseinstellungen und
lädt sie aus Umgebungsvariablen.

Autor: Lukas Dönges
Datum: Dezember 2025
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass
class Config:
    """Zentrale Konfigurationsklasse für die Anwendung."""

    # Server-Konfiguration
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    DEBUG: bool = False
    CORS_ALLOWED_ORIGINS: Union[str, list[str]] = "*"

    # Authentifizierung
    AUTH_SECRET_KEY: Optional[str] = None

    # Backend-Endpoints
    SAVE_SUBTITLE_ENDPOINT: Optional[str] = None

    # Whisper-Konfiguration
    WHISPER_MODEL: str = "small"

    # Download-Konfiguration
    DOWNLOAD_CHUNK_SIZE: int = 8192
    DOWNLOAD_TIMEOUT: int = 30

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @classmethod
    def from_env(cls) -> "Config":
        """
        Erstellt eine Konfiguration aus Umgebungsvariablen.

        Returns:
            Config-Instanz mit Werten aus der Umgebung.
        """

        cors_env = os.getenv("CORS_ALLOWED_ORIGINS")

        if cors_env is None or cors_env.strip() == "":
            cors_allowed_origins = "*"
        else:
            origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
            cors_allowed_origins = origins[0] if len(origins) == 1 else origins

        return cls(
            HOST=os.getenv("HOST", "0.0.0.0"),
            PORT=int(os.getenv("PORT", "5000")),
            DEBUG=os.getenv("DEBUG", "False").lower() == "true",
            AUTH_SECRET_KEY=os.getenv("AUTH_SECRET_KEY"),
            SAVE_SUBTITLE_ENDPOINT=os.getenv("SAVE_SUBTITLE_ENDPOINT"),
            CORS_ALLOWED_ORIGINS=cors_allowed_origins,
            WHISPER_MODEL=os.getenv("WHISPER_MODEL", "small"),
            DOWNLOAD_CHUNK_SIZE=int(os.getenv("DOWNLOAD_CHUNK_SIZE", "8192")),
            DOWNLOAD_TIMEOUT=int(os.getenv("DOWNLOAD_TIMEOUT", "30")),
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
            LOG_FORMAT=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        )

    def validate(self) -> bool:
        """
        Validiert die Konfiguration.

        Returns:
            True wenn alle erforderlichen Werte gesetzt sind.

        Raises:
            ValueError: Wenn erforderliche Konfigurationswerte fehlen.
        """
        errors = []

        if not self.AUTH_SECRET_KEY:
            errors.append("AUTH_SECRET_KEY ist nicht konfiguriert")

        if not self.SAVE_SUBTITLE_ENDPOINT:
            errors.append("SAVE_SUBTITLE_ENDPOINT ist nicht konfiguriert")

        if self.WHISPER_MODEL not in ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "turbo"]:
            errors.append(f"Ungültiges Whisper-Modell: {self.WHISPER_MODEL}")

        if errors:
            raise ValueError(f"Konfigurationsfehler: {', '.join(errors)}")

        return True


# Globale Konfigurationsinstanz
config = Config.from_env()

