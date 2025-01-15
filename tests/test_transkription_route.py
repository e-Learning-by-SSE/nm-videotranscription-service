import os
import pytest
import jwt
from unittest.mock import patch, MagicMock
from flask_socketio import SocketIOTestClient
from app import app, socketio, verify_token, tasks


@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def socketio_client():
    return SocketIOTestClient(app, socketio)


def test_verify_token_valid():
    secret_key = "test_secret_key"
    payload = {"user_id": 123}
    token = jwt.encode(payload, secret_key, algorithm="HS256")

    with patch.dict(os.environ, {"AUTH_SECRET_KEY": secret_key}):
        decoded = verify_token(token)
        assert decoded == payload


def test_verify_token_invalid():
    secret_key = "test_secret_key"
    token = "invalid.token.string"

    with patch.dict(os.environ, {"AUTH_SECRET_KEY": secret_key}):
        decoded = verify_token(token)
        assert decoded is None


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Flask-SocketIO Whisper transcription service is running." in response.data


def test_handle_transcription(socketio_client):
    with patch("app.verify_token", return_value={"user_id": 123}), \
         patch("app.threading.Thread.start", return_value=None) as mock_thread_start:

        socketio_client.emit("transcribe", {
            "bearer_token": "valid_token",
            "video_url": "http://example.com/video.mp4",
            "lessonId": "lesson_1",
            "realtime": True,
            "task_id": "test_task_123"
        })

        received = socketio_client.get_received()
        assert any(event["name"] == "task_started" for event in received)
        assert tasks[socketio_client.sid]["task_id"] == "test_task_123"
        mock_thread_start.assert_called_once()


def test_handle_transcription_invalid_token(socketio_client):
    with patch("app.verify_token", return_value=None):
        socketio_client.emit("transcribe", {
            "bearer_token": "invalid_token",
            "video_url": "http://example.com/video.mp4",
            "lessonId": "lesson_1",
        })

        received = socketio_client.get_received()
        assert any(event["name"] == "error" and event["args"][0]["message"] == "Invalid or expired token" for event in received)


def test_handle_transcription_missing_video_url(socketio_client):
    with patch("app.verify_token", return_value={"user_id": 123}):
        socketio_client.emit("transcribe", {
            "bearer_token": "valid_token",
        })

        received = socketio_client.get_received()
        assert any(event["name"] == "error" and event["args"][0]["message"] == "Video URL is required" for event in received)


def test_handle_disconnect(socketio_client):
    with patch("app.tasks", new_callable=lambda: {socketio_client.sid: {"task_id": "test_task_123", "active": True, "realtime": True}}):
        socketio_client.disconnect()

        assert socketio_client.sid not in tasks


def test_background_task():
    task_id = "test_task_123"
    video_url = "http://example.com/video.mp4"
    lesson_id = "lesson_1"
    token = "test_token"
    client_sid = "test_sid"

    with patch("app.download_video"), \
         patch("app.extract_audio"), \
         patch("app.whisper.load_model"), \
         patch("app.transcribe_audio_with_progress", return_value="Test transcription"), \
         patch("app.requests.post") as mock_post:

        mock_post.return_value.status_code = 200

        app.background_task(task_id, video_url, lesson_id, token, client_sid, realtime=False)
        mock_post.assert_called_once()
        assert "Test transcription" in mock_post.call_args[1]["json"]["transcription"]
