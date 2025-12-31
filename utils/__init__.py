"""
Utils-Paket für das Selflearn Transkriptions-Backend

Dieses Paket enthält Hilfsfunktionen für:
- Audio-Extraktion aus Videos (audio_extraction)
- Video-Download (download_video)
- Datei-Verwaltung (file_manager)
- Transkription mit Whisper (transcribe)

Autor: Lukas Dönges
Datum: Dezember 2025
"""

from .audio_extraction import extract_audio
from .download_video import download_video
from .transcribe import transcribe_audio_with_progress

__all__ = [
    'extract_audio',
    'download_video',
    'transcribe_audio_with_progress'
]

