"""
Transkriptions-Modul

Dieses Modul bietet Funktionalität zur Transkription von Audio-Dateien
mithilfe des OpenAI Whisper-Modells.

Autor: Lukas Dönges
Datum: Dezember 2025
"""

import logging
from typing import Dict, Any, List, Optional
from utils.whisper_context_manager import capture_whisper_progress

logger = logging.getLogger(__name__)

def format_timestamp(seconds: float) -> str:
    """
    Konvertiert Sekunden in ein lesbares Zeitformat (HH:MM:SS).

    Args:
        seconds: Zeit in Sekunden.

    Returns:
        Formatierte Zeitangabe als String.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def extract_segments(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrahiert und formatiert die Segmente aus dem Whisper-Ergebnis.

    Args:
        result: Das Rohergebnis der Whisper-Transkription.

    Returns:
        Liste von formatierten Segment-Dictionaries mit Start, Ende und Text.
    """
    segments = []
    for segment in result.get('segments', []):
        segments.append({
            'start': segment.get('start', 0),
            'end': segment.get('end', 0),
            'start_formatted': format_timestamp(segment.get('start', 0)),
            'end_formatted': format_timestamp(segment.get('end', 0)),
            'text': segment.get('text', '').strip()
        })
    return segments


def transcribe_audio_with_progress(
    model,
    audio_file_path: str,
    language: Optional[str] = None,
    send_progress_fn = None
) -> Dict[str, Any]:
    """
    Transkribiert eine Audio-Datei mit dem Whisper-Modell.

    Diese Funktion führt die eigentliche Transkription durch und
    strukturiert das Ergebnis für die weitere Verarbeitung.

    Args:
        model: Das geladene Whisper-Modell.
        audio_file_path: Pfad zur Audio-Datei.
        language: Optional die Sprache des Audios (z.B. 'de', 'en').
                  Wenn None, wird die Sprache automatisch erkannt.

    Returns:
        Dictionary mit Transkriptionsergebnis:
            - text: Der vollständige transkribierte Text.
            - segments: Liste der einzelnen Segmente mit Zeitstempeln.
            - language: Die erkannte oder angegebene Sprache.
            - duration: Gesamtdauer der Audio-Datei.

    Raises:
        FileNotFoundError: Wenn die Audio-Datei nicht existiert.
        RuntimeError: Bei Fehlern während der Transkription.
    """
    logger.info(f"Starte Transkription: {audio_file_path}")

    try:
        # Transkriptions-Optionen
        transcribe_options = {
            'fp16': False,  # CPU-kompatibel
            'verbose': False
        }

        # Sprache setzen falls angegeben
        if language:
            transcribe_options['language'] = language
            logger.info(f"Sprache festgelegt: {language}")

        # Transkription durchführen
        with capture_whisper_progress(send_progress_fn=send_progress_fn):
            result = model.transcribe(audio_file_path, **transcribe_options)
        if send_progress_fn:
            send_progress_fn('Transkription abgeschlossen.')

        # Ergebnis strukturieren
        transcription = {
            'text': result.get('text', '').strip(),
            'segments': extract_segments(result),
            'language': result.get('language', 'unknown'),
            'duration': result.get('segments', [{}])[-1].get('end', 0) if result.get('segments') else 0
        }

        logger.info(
            f"Transkription abgeschlossen: "
            f"{len(transcription['segments'])} Segmente, "
            f"Sprache: {transcription['language']}, "
            f"Dauer: {format_timestamp(transcription['duration'])}"
        )

        return transcription

    except FileNotFoundError:
        logger.error(f"Audio-Datei nicht gefunden: {audio_file_path}")
        raise

    except Exception as e:
        logger.error(f"Fehler bei der Transkription: {e}", exc_info=True)
        raise RuntimeError(f"Transkription fehlgeschlagen: {e}")
