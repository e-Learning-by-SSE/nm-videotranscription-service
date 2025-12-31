"""
Video-Download-Modul

Dieses Modul bietet Funktionalität zum Herunterladen von Videos
von einer URL mit Fortschrittsanzeige über WebSocket.

Autor: Lukas Dönges
Datum: Dezember 2025
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Konstanten für Download-Konfiguration
CHUNK_SIZE = 8192  # Bytes pro Chunk
PROGRESS_UPDATE_INTERVAL = 5  # Prozent-Schritte für Updates


def download_video(
    video_url: str,
    save_path: str,
    socketio=None,
    client_sid: Optional[str] = None
) -> None:
    """
    Lädt ein Video von einer URL herunter und speichert es lokal.

    Diese Funktion lädt ein Video streambasiert herunter und sendet
    optional Fortschrittsupdates über WebSocket an den Client.

    Args:
        video_url: Die URL des herunterzuladenden Videos.
        save_path: Der lokale Pfad, unter dem das Video gespeichert wird.
        socketio: SocketIO-Instanz für WebSocket-Kommunikation (optional).
        client_sid: Session-ID des Clients für Fortschrittsupdates (optional).

    Raises:
        requests.RequestException: Bei Netzwerkfehlern.
        ValueError: Wenn die URL ungültig ist oder der Server nicht antwortet.
        IOError: Bei Fehlern beim Schreiben der Datei.
    """
    logger.info(f"Starte Download von: {video_url}")

    try:
        # HTTP-Request mit Stream-Mode für effizientes Herunterladen großer Dateien
        response = requests.get(
            video_url,
            stream=True,
            timeout=30,
            headers={'User-Agent': 'Selflearn-Transcription-Service/1.0'}
        )
        response.raise_for_status()

        # Dateigröße ermitteln
        total_length = response.headers.get('content-length')
        if total_length is None:
            logger.warning("Content-Length nicht verfügbar, kein Fortschritt möglich")
            total_length = 0
        else:
            total_length = int(total_length)
            logger.debug(f"Download-Größe: {total_length / (1024 * 1024):.2f} MB")

        # Datei schreiben mit Fortschrittsanzeige
        downloaded = 0
        last_percent = 0

        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    file.write(chunk)
                    downloaded += len(chunk)

                    # Fortschritt berechnen und senden
                    if total_length > 0:
                        percent = int((downloaded / total_length) * 100)

                        # Nur bei signifikanter Änderung senden
                        if percent >= last_percent + PROGRESS_UPDATE_INTERVAL:
                            last_percent = percent
                            logger.debug(f"Download-Fortschritt: {percent}%")

                            if socketio and client_sid:
                                socketio.emit(
                                    'progress',
                                    {'message': f'Video wird heruntergeladen... {percent}%'},
                                    to=client_sid
                                )

        logger.info(f"Download abgeschlossen: {save_path} ({downloaded / (1024 * 1024):.2f} MB)")

    except requests.exceptions.Timeout:
        logger.error(f"Timeout beim Download von: {video_url}")
        raise ValueError(f"Zeitüberschreitung beim Download von {video_url}")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP-Fehler beim Download: {e}")
        raise ValueError(f"Server-Fehler: {e}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Netzwerkfehler beim Download: {e}")
        raise

    except IOError as e:
        logger.error(f"Fehler beim Schreiben der Datei: {e}")
        raise
