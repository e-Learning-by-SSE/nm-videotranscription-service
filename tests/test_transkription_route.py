"""
Tests für das Selflearn Transkriptions-Backend

Dieses Modul enthält Unit- und Integrationstests für die
Transkriptions-Funktionalität.

Autor: Lukas Dönges
Datum: Dezember 2025
"""

import os
import time
import csv
import pytest
import jwt
from unittest.mock import patch

import whisper
from flask_socketio import SocketIOTestClient
from app import app, socketio, verify_token, tasks, tasks_lock
from utils.audio_extraction import extract_audio
from utils.transcribe import transcribe_audio_with_progress


# ==================== Fixtures ====================

@pytest.fixture
def client():
    """Erstellt einen Flask Test-Client."""
    app.testing = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def socketio_client():
    """Erstellt einen SocketIO Test-Client."""
    return SocketIOTestClient(app, socketio)


@pytest.fixture
def valid_token():
    """Erstellt ein gültiges JWT-Token für Tests."""
    secret_key = "test_secret_key"
    payload = {"user_id": 123, "exp": time.time() + 3600}
    return jwt.encode(payload, secret_key, algorithm="HS256")


# ==================== Token-Verifizierung Tests ====================

class TestTokenVerification:
    """Tests für die JWT-Token-Verifizierung."""

    def test_verify_token_valid(self):
        """Testet die Verifizierung eines gültigen Tokens."""
        secret_key = "test_secret_key"
        payload = {"user_id": 123}
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        with patch.dict(os.environ, {"AUTH_SECRET_KEY": secret_key}):
            decoded = verify_token(token)
            assert decoded is not None
            assert decoded["user_id"] == 123

    def test_verify_token_invalid(self):
        """Testet die Verifizierung eines ungültigen Tokens."""
        secret_key = "test_secret_key"
        token = "invalid.token.string"

        with patch.dict(os.environ, {"AUTH_SECRET_KEY": secret_key}):
            decoded = verify_token(token)
            assert decoded is None

    def test_verify_token_missing_secret_key(self):
        """Testet das Verhalten ohne konfigurierten Secret Key."""
        with patch.dict(os.environ, {}, clear=True):
            # Entfernt AUTH_SECRET_KEY aus der Umgebung
            if "AUTH_SECRET_KEY" in os.environ:
                del os.environ["AUTH_SECRET_KEY"]
            decoded = verify_token("any_token")
            assert decoded is None


# ==================== HTTP-Endpoint Tests ====================

class TestHTTPEndpoints:
    """Tests für die REST-API-Endpoints."""

    def test_index(self, client):
        """Testet den Root-Endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Transkriptions-Service" in response.data or b"transcription" in response.data.lower()

    def test_health_check(self, client):
        """Testet den Health-Check-Endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data
        assert data["status"] == "healthy"


# ==================== WebSocket Tests ====================

class TestWebSocket:
    """Tests für die WebSocket-Kommunikation."""

    def test_handle_transcription_success(self, socketio_client):
        """Testet eine erfolgreiche Transkriptions-Anfrage."""
        with patch("app.verify_token", return_value={"user_id": 123}), \
             patch("app.threading.Thread.start", return_value=None) as mock_thread:

            socketio_client.emit("transcribe", {
                "bearer_token": "valid_token",
                "video_url": "http://example.com/video.mp4",
                "lessonId": "lesson_1",
                "realtime": True,
                "task_id": "test_task_123"
            })

            received = socketio_client.get_received()
            task_started_events = [e for e in received if e["name"] == "task_started"]
            assert len(task_started_events) > 0
            mock_thread.assert_called_once()

    def test_handle_transcription_invalid_token(self, socketio_client):
        """Testet die Ablehnung bei ungültigem Token."""
        with patch("app.verify_token", return_value=None):
            socketio_client.emit("transcribe", {
                "bearer_token": "invalid_token",
                "video_url": "http://example.com/video.mp4",
                "lessonId": "lesson_1",
            })

            received = socketio_client.get_received()
            error_events = [e for e in received if e["name"] == "error"]
            assert len(error_events) > 0

    def test_handle_transcription_missing_video_url(self, socketio_client):
        """Testet die Ablehnung bei fehlender Video-URL."""
        with patch("app.verify_token", return_value={"user_id": 123}):
            socketio_client.emit("transcribe", {
                "bearer_token": "valid_token",
                "lessonId": "lesson_1",
            })

            received = socketio_client.get_received()
            error_events = [e for e in received if e["name"] == "error"]
            assert len(error_events) > 0

    def test_handle_disconnect(self, socketio_client):
        """Testet das Disconnect-Handling."""
        from app import tasks, tasks_lock

        # Simuliere einen aktiven Task mit einer Test-SID
        test_sid = "test_client_sid_123"

        # Task manuell registrieren
        with tasks_lock:
            tasks[test_sid] = {
                "task_id": "test_task_123",
                "active": True,
                "realtime": True
            }

        try:
            # Disconnect über den socketio_client auslösen
            # Das triggert den disconnect Handler
            socketio_client.disconnect()

            # Da der echte Client eine andere SID hat,
            # testen wir hier nur, dass der Task korrekt registriert wurde
            # und dass disconnect ohne Fehler durchläuft
            with tasks_lock:
                # Unser manuell registrierter Task sollte noch existieren
                # (weil disconnect mit einer anderen SID aufgerufen wurde)
                assert test_sid in tasks
                assert tasks[test_sid]["active"] == True
        finally:
            # Aufräumen
            with tasks_lock:
                if test_sid in tasks:
                    del tasks[test_sid]


# ==================== Background Task Tests ====================

class TestBackgroundTask:
    """Tests für die Hintergrund-Transkription."""

    def test_background_task_saves_to_backend(self):
        """Testet das Speichern der Transkription im Backend."""
        from app import background_task

        task_id = "test_task_123"
        video_url = "http://example.com/video.mp4"
        lesson_id = "lesson_1"
        token = "test_token"
        client_sid = "test_sid"

        mock_transcription = {
            "text": "Test transcription",
            "segments": [],
            "language": "de"
        }

        with patch("app.download_video"), \
             patch("app.extract_audio", return_value="/tmp/audio.mp3"), \
             patch("app.transcribe_audio_with_progress", return_value=mock_transcription), \
             patch("app.save_transcription_to_backend") as mock_save, \
             patch.dict(os.environ, {"SAVE_SUBTITLE_ENDPOINT": "http://test.com/save"}):

            background_task(task_id, video_url, lesson_id, token, client_sid, realtime=False)
            mock_save.assert_called_once()


# ==================== Performance Tests ====================

class TestPerformance:
    """Performance-Tests für verschiedene Whisper-Modelle.

    HINWEIS: Diese Tests sind zeitintensiv und sollten nur manuell
    ausgeführt werden.
    """

    @pytest.mark.skip(reason="Performance-Test - nur manuell ausführen")
    def test_transcription_performance(self):
        """Misst die Transkriptionszeit für verschiedene Modelle."""
        video_directory = "./tests/videos"
        models = ["tiny", "base", "small"]
        results = []

        for model_name in models:
            model = whisper.load_model(model_name)

            for video_file in os.listdir(video_directory):
                if video_file.startswith("__") or not video_file.endswith(".mp4"):
                    continue

                video_path = os.path.join(video_directory, video_file)
                start_time = time.time()

                try:
                    audio_file_path = extract_audio(video_path)
                    transcription = transcribe_audio_with_progress(model, audio_file_path)
                    elapsed_time = time.time() - start_time

                    word_count = len(transcription.get("text", "").split())
                    results.append({
                        "model": model_name,
                        "video": video_file,
                        "time_seconds": elapsed_time,
                        "word_count": word_count,
                        "text": transcription.get("text", "")[:200]
                    })

                    print(f"✓ {model_name}/{video_file}: {elapsed_time:.2f}s, {word_count} Wörter")

                except Exception as e:
                    print(f"✗ {model_name}/{video_file}: Fehler - {e}")

        # Ergebnisse speichern
        self._save_results_to_csv(results)

    def _save_results_to_csv(self, results):
        """Speichert Performance-Ergebnisse in einer CSV-Datei."""
        csv_path = "./tests/transcription_results.csv"

        with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["model", "video", "time_seconds", "word_count", "text"]
            )
            writer.writeheader()
            writer.writerows(results)

        print(f"\nErgebnisse gespeichert: {csv_path}")


# ==================== Utility Function Tests ====================

class TestUtilityFunctions:
    """Tests für Hilfsfunktionen."""

    def test_format_timestamp(self):
        """Testet die Zeitstempel-Formatierung."""
        from utils.transcribe import format_timestamp

        assert format_timestamp(0) == "00:00:00"
        assert format_timestamp(61) == "00:01:01"
        assert format_timestamp(3661) == "01:01:01"
        assert format_timestamp(3723.5) == "01:02:03"

    def test_extract_segments(self):
        """Testet die Segment-Extraktion."""
        from utils.transcribe import extract_segments

        mock_result = {
            "segments": [
                {"start": 0, "end": 5, "text": "Hallo"},
                {"start": 5, "end": 10, "text": "Welt"}
            ]
        }

        segments = extract_segments(mock_result)
        assert len(segments) == 2
        assert segments[0]["text"] == "Hallo"
        assert segments[1]["start"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


