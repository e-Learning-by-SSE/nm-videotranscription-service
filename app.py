"""
Selflearn Transkriptions-Backend

Dieses Modul stellt einen Flask-SocketIO Server bereit, der Video-Dateien
transkribiert. Es verwendet OpenAI Whisper für die Spracherkennung und
kommuniziert in Echtzeit mit dem Client über WebSockets.

Autor: Lukas Dönges
Datum: Dezember 2025
Universität: Universität Hildesheim
"""

import os
import tempfile
import threading
import time
import logging
from typing import Dict, Any, Optional

import jwt
import requests
import whisper
from flask import Flask, request
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

load_dotenv()
from config import config as app_config

app_config.validate()

from utils.audio_extraction import extract_audio
from utils.audio_extraction import has_audio_stream
from utils.download_video import download_video
from utils.transcribe import transcribe_audio_with_progress


# Logging-Konfiguration
logging.basicConfig(level=app_config.LOG_LEVEL, format=app_config.LOG_FORMAT)
logger = logging.getLogger(__name__)

# Flask-Anwendung initialisieren
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins=app_config.CORS_ALLOWED_ORIGINS)

# Thread-safe Dictionary zur Verwaltung aktiver Transkriptions-Tasks
tasks: Dict[str, Dict[str, Any]] = {}
tasks_lock = threading.Lock()

# Whisper-Modell beim Start laden
logger.info(f"Lade Whisper-Modell: {app_config.WHISPER_MODEL} ...")
MODEL = whisper.load_model(app_config.WHISPER_MODEL)
model_lock = threading.Lock()
logger.info("Whisper-Modell erfolgreich geladen.")


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifiziert ein JWT-Token und gibt die dekodierten Daten zurück.

    Args:
        token: Das zu verifizierende JWT-Token.

    Returns:
        Die dekodierten Token-Daten bei Erfolg, None bei ungültigem Token.
    """
    try:
        secret_key = app_config.AUTH_SECRET_KEY
        if not secret_key:
            logger.error("AUTH_SECRET_KEY ist nicht konfiguriert")
            return None
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        logger.warning("Token ist abgelaufen")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Ungültiges Token: {e}")
        return None


def send_progress(client_sid: str, task_id: str, message: str, realtime: bool = True) -> None:
    """
    Sendet eine Fortschrittsnachricht an den Client.

    Args:
        client_sid: Die Session-ID des Clients.
        task_id: Die ID der aktuellen Aufgabe.
        message: Die zu sendende Nachricht.
        realtime: Ob Echtzeit-Updates aktiviert sind.
    """
    if realtime and client_sid:
        socketio.emit('progress', {'task_id': task_id, 'message': message}, to=client_sid)
        logger.debug(f"Progress gesendet: {message}")

def create_send_progress(client_sid, task_id, realtime=True):
    """
    Erstellt eine Wrapper-Funktion zum Senden von Fortschrittsnachrichten, die in WhisperProgressRedirector verwendet werden kann.
    Der Vorteil ist, dass für die Verwendung des Wrappers die Argumente client_sid, task_id und realtime nicht mehr an die fremde
    Komponente übergeben werden müssen -> geringere Kopplung und einfachere Integration in WhisperProgressRedirector.
    Args:
        client_sid: Die Session-ID des Clients.
        task_id: Die ID der aktuellen Aufgabe.
        realtime: Ob Echtzeit-Updates aktiviert sind.
    Returns:
        Eine Funktion, die eine Nachricht entgegennimmt und sie als Fortschrittsupdate sendet.
    """
    def send_progress_wrapper(message: str):
        send_progress(client_sid, task_id, message, realtime)
    return send_progress_wrapper

def save_transcription_to_backend(
    task_id: str,
    transcription: Dict[str, Any],
    lesson_id: str,
    token: str
) -> bool:
    """
    Speichert die Transkription im Backend-Server.

    Args:
        task_id: Die ID der Aufgabe.
        transcription: Die Transkriptionsdaten.
        lesson_id: Die ID der Lektion.
        token: Das Authentifizierungs-Token.

    Returns:
        True bei Erfolg, False bei Fehler.
    """
    backend_url = app_config.SAVE_SUBTITLE_ENDPOINT
    if not backend_url:
        logger.error("SAVE_SUBTITLE_ENDPOINT ist nicht konfiguriert")
        return False

    try:
        response = requests.post(
            backend_url,
            json={
                'task_id': task_id,
                'transcription': transcription,
                'lessonId': lesson_id
            },
            headers={'Authorization': f'Bearer {token}'},
            timeout=app_config.DOWNLOAD_TIMEOUT
        )

        if response.status_code == 200:
            logger.info(f"Task {task_id}: Transkription erfolgreich gespeichert")
            return True
        else:
            logger.error(
                f"Task {task_id}: Fehler beim Speichern. "
                f"Status: {response.status_code}, Antwort: {response.text}"
            )
            return False
    except requests.RequestException as e:
        logger.error(f"Task {task_id}: Netzwerkfehler beim Speichern: {e}")
        return False


def background_task(
    task_id: str,
    video_url: str,
    lesson_id: str,
    token: str,
    client_sid: Optional[str] = None,
    realtime: bool = True
) -> None:
    """
    Führt die Transkription als Hintergrund-Task aus.

    Diese Funktion lädt ein Video herunter, extrahiert das Audio,
    führt die Transkription durch und sendet das Ergebnis zurück.

    Args:
        task_id: Eindeutige ID für diesen Task.
        video_url: URL des zu transkribierenden Videos.
        lesson_id: ID der zugehörigen Lektion.
        token: Authentifizierungs-Token.
        client_sid: Session-ID des Clients für WebSocket-Kommunikation.
        realtime: Ob Echtzeit-Updates gesendet werden sollen.
    """
    logger.info(f"Task {task_id}: Starte Transkription für {video_url}")
    send_progress_fn = create_send_progress(client_sid, task_id, realtime)

    try:
        with tempfile.TemporaryDirectory() as tmpdirname:
            video_file_path = os.path.join(tmpdirname, "temp_video.mp4")

            # Schritt 1: Video herunterladen
            send_progress_fn('Video wird heruntergeladen...')
            download_video(video_url, video_file_path, client_sid=client_sid, socketio=socketio)
            logger.info(f"Task {task_id}: Video erfolgreich heruntergeladen")

            # Schritt 2: Audio extrahieren
            if has_audio_stream(video_file_path):
                send_progress_fn('Audio wird extrahiert...')
                audio_file_path = extract_audio(video_file_path, socketio=socketio, client_sid=client_sid)
                logger.info(f"Task {task_id}: Audio erfolgreich extrahiert")
            else:
                error_msg = "Video enthält keine Audio-Spur."
                send_progress_fn(error_msg)
                logger.error(f"Task {task_id}: {error_msg}")
                return

            # Schritt 3: Transkription durchführen (thread-safe mit model_lock)
            send_progress_fn('Transkription läuft...')
            with model_lock:
                transcription = transcribe_audio_with_progress(MODEL, audio_file_path, send_progress_fn=send_progress_fn)
            logger.info(f"Task {task_id}: Transkription erfolgreich abgeschlossen")

            # Ergebnis zusammenstellen
            result = {'task_id': task_id, 'transcription': transcription}

            # Ergebnis senden oder speichern (thread-safe Zugriff)
            with tasks_lock:
                is_active = client_sid in tasks and tasks[client_sid].get('active', False)
                should_emit_realtime = realtime and is_active

            if should_emit_realtime:
                socketio.emit('complete', result, to=client_sid)
                logger.info(f"Task {task_id}: Ergebnis an Client gesendet")
            else:
                save_transcription_to_backend(task_id, transcription, lesson_id, token)

    except FileNotFoundError as e:
        error_msg = f"Datei nicht gefunden: {e}"
        logger.error(f"Task {task_id}: {error_msg}")
        if realtime and client_sid:
            socketio.emit('error', {'task_id': task_id, 'message': error_msg}, to=client_sid)

    except requests.RequestException as e:
        error_msg = f"Netzwerkfehler beim Download: {e}"
        logger.error(f"Task {task_id}: {error_msg}")
        if realtime and client_sid:
            socketio.emit('error', {'task_id': task_id, 'message': error_msg}, to=client_sid)

    except Exception as e:
        error_msg = f"Unerwarteter Fehler: {e}"
        logger.error(f"Task {task_id}: {error_msg}", exc_info=True)
        if realtime and client_sid:
            socketio.emit('error', {'task_id': task_id, 'message': error_msg}, to=client_sid)

    finally:
        # Task aus der Verwaltung entfernen (thread-safe)
        with tasks_lock:
            if client_sid in tasks:
                del tasks[client_sid]
                logger.debug(f"Task {task_id}: Aus Verwaltung entfernt")


@socketio.on('transcribe')
def handle_transcription(data: Dict[str, Any]) -> None:
    """
    WebSocket-Handler für Transkriptions-Anfragen.

    Erwartet folgende Daten:
        - bearer_token: JWT-Token für die Authentifizierung
        - video_url: URL des zu transkribierenden Videos
        - lessonId: ID der zugehörigen Lektion
        - realtime: (optional) Ob Echtzeit-Updates gewünscht sind
        - task_id: (optional) Benutzerdefinierte Task-ID

    Args:
        data: Dictionary mit den Anfrage-Daten.
    """
    # Token validieren
    token = data.get('bearer_token')
    decoded_token = verify_token(token)
    if decoded_token is None:
        emit('error', {'message': 'Ungültiges oder abgelaufenes Token'})
        logger.warning("Transkriptions-Anfrage mit ungültigem Token abgelehnt")
        return

    client_sid = request.sid
    # Parameter extrahieren
    video_url = data.get('video_url')
    lesson_id = data.get('lessonId')
    realtime = data.get('realtime', True)
    task_id = data.get('task_id', f"task_{int(time.time())}")

    # Validierung
    if not video_url:
        emit('error', {'message': 'Video-URL ist erforderlich'})
        logger.warning("Transkriptions-Anfrage ohne Video-URL abgelehnt")
        return

    # Task registrieren (thread-safe) - prüfe auf existierenden aktiven Task
    with tasks_lock:
        if client_sid in tasks and tasks[client_sid].get('active', False):
            emit('error', {'message': 'Es läuft bereits ein Task für diesen Client. Bitte warten.'})
            logger.warning(f"Task-Anfrage abgelehnt: Client {client_sid} hat bereits einen aktiven Task")
            return

        tasks[client_sid] = {
            'task_id': task_id,
            'active': True,
            'realtime': realtime
        }
    logger.info(f"Neuer Task registriert: {task_id} für Client {client_sid}")

    # Hintergrund-Thread starten
    thread = threading.Thread(
        target=background_task,
        args=(task_id, video_url, lesson_id, token, client_sid, realtime),
        daemon=True
    )
    thread.start()

    emit('task_started', {'task_id': task_id, 'message': 'Task gestartet'})


@socketio.on('disconnect')
def handle_disconnect() -> None:
    """
    WebSocket-Handler für Client-Disconnects.

    Markiert aktive Tasks als inaktiv, damit diese im Hintergrund
    fortgesetzt werden können.
    """
    client_sid = request.sid
    with tasks_lock:
        if client_sid in tasks:
            tasks[client_sid]['active'] = False
            tasks[client_sid]['realtime'] = False
            logger.info(
                f"Client {client_sid} getrennt. "
                f"Task {tasks[client_sid]['task_id']} als inaktiv markiert."
            )


@socketio.on('connect')
def handle_connect() -> None:
    """WebSocket-Handler für neue Client-Verbindungen."""
    client_sid = request.sid
    logger.info(f"Neuer Client verbunden: {client_sid}")


@app.route('/')
def index() -> str:
    """
    Root-Endpoint für Health-Checks.

    Returns:
        Status-Nachricht als String.
    """
    return "Flask-SocketIO Whisper Transkriptions-Service läuft."


@app.route('/health')
def health_check() -> Dict[str, Any]:
    """
    Health-Check Endpoint für Monitoring.

    Returns:
        JSON mit Status-Informationen.
    """
    with tasks_lock:
        active_task_count = len(tasks)

    return {
        'status': 'healthy',
        'model_loaded': MODEL is not None,
        'active_tasks': active_task_count
    }


if __name__ == '__main__':
    # Server starten
    logger.info(f"Starte Server auf {app_config.HOST}:{app_config.PORT} (Debug: {app_config.DEBUG})")
    socketio.run(app, host=app_config.HOST, port=app_config.PORT, debug=app_config.DEBUG)
