"""
Audio-Extraktions-Modul

Dieses Modul bietet Funktionalität zum Extrahieren von Audio-Spuren
aus Video-Dateien mithilfe von FFmpeg.

Autor: Lukas Dönges
Datum: Dezember 2025
"""

import re
import subprocess
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_video_duration(video_file_path: str) -> float:
    """
    Ermittelt die Dauer eines Videos in Sekunden.

    Args:
        video_file_path: Pfad zur Video-Datei.

    Returns:
        Die Dauer des Videos in Sekunden.

    Raises:
        subprocess.CalledProcessError: Wenn ffprobe fehlschlägt.
        ValueError: Wenn die Dauer nicht ermittelt werden kann.
    """
    command = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_file_path
    ]

    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        duration = float(output.decode('utf-8').strip())
        logger.debug(f"Video-Dauer ermittelt: {duration:.2f} Sekunden")
        return duration
    except subprocess.CalledProcessError as e:
        logger.error(f"Fehler bei ffprobe: {e}")
        raise
    except ValueError as e:
        logger.error(f"Ungültiges Dauer-Format: {e}")
        raise

def has_audio_stream(video_file_path: str) -> bool:
    """
    Prüft, ob eine Video-Datei mindestens eine Audio-Spur enthält.

    Args:
        video_file_path: Pfad zur Video-Datei.

    Returns:
        True, wenn mindestens ein Audio-Stream vorhanden ist, sonst False.

    Raises:
        FileNotFoundError: Wenn die Datei nicht existiert.
        RuntimeError: Wenn ffprobe fehlschlägt.
    """
    if not os.path.exists(video_file_path):
        raise FileNotFoundError(f"Datei nicht gefunden: {video_file_path}")

    command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index",
        "-of", "csv=p=0",
        video_file_path
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    if result.returncode != 0:
        logger.error(f"ffprobe-Fehler:\n{result.stderr}")
        raise RuntimeError(f"ffprobe fehlgeschlagen: {result.stderr}")

    # Wenn stdout leer ist → kein Audio
    has_audio = bool(result.stdout.strip())

    logger.debug(f"Audio-Stream vorhanden: {has_audio}")
    return has_audio


def extract_audio(
    video_file_path: str,
    client_sid: Optional[str] = None,
    socketio=None
) -> str:
    """
    Extrahiert die Audio-Spur aus einer Video-Datei.

    Diese Funktion verwendet FFmpeg, um die Audio-Spur aus einem Video
    zu extrahieren und als MP3-Datei zu speichern. Optional werden
    Fortschrittsupdates über WebSocket gesendet.

    Args:
        video_file_path: Pfad zur Video-Datei.
        client_sid: Session-ID des Clients für Fortschrittsupdates.
        socketio: SocketIO-Instanz für WebSocket-Kommunikation.

    Returns:
        Pfad zur extrahierten Audio-Datei.

    Raises:
        FileNotFoundError: Wenn die Video-Datei nicht existiert.
        subprocess.CalledProcessError: Wenn FFmpeg fehlschlägt.
    """
    # Temporäre Datei für Audio erstellen
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
        audio_file_path = temp_audio.name

    logger.info(f"Extrahiere Audio: {video_file_path} -> {audio_file_path}")

    # Video-Dauer ermitteln für Fortschrittsberechnung
    try:
        duration = get_video_duration(video_file_path)
    except Exception:
        duration = 0
        logger.warning("Konnte Video-Dauer nicht ermitteln, kein Fortschritt verfügbar")

    # FFmpeg-Befehl zusammenstellen
    command = [
        'ffmpeg',
        '-y',                   # Überschreibe existierende Dateien
        '-i', video_file_path,  # Eingabe-Datei
        '-vn',                  # Keine Video-Verarbeitung
        '-acodec', 'libmp3lame', # MP3-Codec
        '-q:a', '2',            # Audio-Qualität (0-9, niedriger = besser)
        audio_file_path         # Ausgabe-Datei
    ]

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        # Regex zum Parsen der FFmpeg-Zeitausgabe
        time_regex = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')
        last_percent = 0

        for line in process.stdout:
            match = time_regex.search(line)
            if match and duration > 0:
                hours, minutes, seconds = map(float, match.groups())
                current_time = hours * 3600 + minutes * 60 + seconds
                percent = min(int((current_time / duration) * 100), 100)

                # Nur bei signifikanter Änderung senden (vermeidet Spam)
                if percent >= last_percent + 5:
                    last_percent = percent
                    logger.debug(f"Audio-Extraktion: {percent}%")

                    if socketio and client_sid:
                        socketio.emit(
                            'progress',
                            {'message': f'Audio wird extrahiert... {percent}%'},
                            to=client_sid
                        )

        # Auf Prozess-Ende warten
        process.wait()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)

        logger.info(f"Audio erfolgreich extrahiert: {audio_file_path}")
        return audio_file_path

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg-Fehler: {e}")
        raise
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei Audio-Extraktion: {e}")
        raise
