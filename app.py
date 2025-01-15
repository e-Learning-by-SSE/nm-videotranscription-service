import os
import tempfile
import threading
import time
import jwt

import requests
import whisper
from flask import Flask, request
from flask_socketio import SocketIO, emit

from dotenv import load_dotenv
from utils.audio_extraction import extract_audio
from utils.download_video import download_video
from utils.transcribe import transcribe_audio_with_progress

load_dotenv()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

tasks = {}


def verify_token(token):
    try:
        decoded = jwt.decode(token, os.getenv("AUTH_SECRET_KEY"), algorithms=["HS256"])
        return decoded
    except jwt.InvalidTokenError:
        return None


def background_task(task_id, video_url, lesson_id, token, client_sid=None, realtime=True):
    try:
        with tempfile.TemporaryDirectory() as tmpdirname:
            video_file_path = os.path.join(tmpdirname, "temp_video.mp4")

            if realtime and client_sid:
                socketio.emit('progress', {'task_id': task_id, 'message': 'Downloading video...'}, to=client_sid)
            download_video(video_url, video_file_path, client_sid=client_sid, socketio=socketio)

            if realtime and client_sid:
                socketio.emit('progress', {'task_id': task_id, 'message': 'Extracting audio...'}, to=client_sid)
            audio_file_path = extract_audio(video_file_path, client_sid=client_sid, socketio=socketio)

            if realtime and client_sid:
                socketio.emit('progress', {'task_id': task_id, 'message': 'Loading transcription model...'},
                              to=client_sid)
            model = whisper.load_model("small")

            if realtime and client_sid:
                socketio.emit('progress', {'task_id': task_id, 'message': 'Transcribing audio...'}, to=client_sid)
            transcription = transcribe_audio_with_progress(model, audio_file_path)

            result = {'task_id': task_id, 'transcription': transcription}

            if realtime and client_sid in tasks and tasks[client_sid].get('active', False):
                socketio.emit('complete', result, to=client_sid)
            else:
                backend_url = os.getenv('SAVE_SUBTITLE_ENDPOINT')
                post_result = requests.post(backend_url, json={'task_id': task_id, 'transcription': transcription,
                                                               'lessonId': lesson_id}, headers={'Authorization': f'Bearer {token}'})
                if post_result.status_code == 200:
                    print(f"Task {task_id} completed. Server URL: {backend_url}")
                else:
                    print(
                        f"Task {task_id} completed. Failed to save transcription to server. Server URL: {backend_url}, Status code: {post_result.status_code}"
                        f"Response: {post_result.text}")

    except Exception as ex:
        error_msg = f"Error processing task {task_id}: {ex} with {video_url} and {lesson_id}. Client SID: {client_sid}. Realtime: {realtime}"
        print(error_msg)
        if realtime and client_sid:
            socketio.emit('error', {'task_id': task_id, 'message': error_msg}, to=client_sid)
    finally:
        if client_sid in tasks:
            del tasks[client_sid]


@socketio.on('transcribe')
def handle_transcription(data):
    token = data.get('bearer_token')
    decoded_token = verify_token(token)
    if decoded_token is None:
        emit('error', {'message': 'Invalid or expired token'})
        return

    video_url = data.get('video_url')
    lesson_id = data.get('lessonId')
    realtime = data.get('realtime', True)
    task_id = data.get('task_id', f"task_{int(time.time())}")
    client_sid = request.sid

    if not video_url:
        emit('error', {'message': 'Video URL is required'})
        return

    tasks[client_sid] = {'task_id': task_id, 'active': True, 'realtime': realtime}

    thread = threading.Thread(target=background_task, args=(task_id, video_url, lesson_id, token, client_sid, realtime))
    thread.start()

    emit('task_started', {'task_id': task_id, 'message': 'Task started'})


@socketio.on('disconnect')
def handle_disconnect():
    client_sid = request.sid
    if client_sid in tasks:
        tasks[client_sid]['active'] = False
        tasks[client_sid]['realtime'] = False
        print(f"Client {client_sid} disconnected. Marking task {tasks[client_sid]['task_id']} as inactive.")


@app.route('/')
def index():
    return "Flask-SocketIO Whisper transcription service is running."


if __name__ == '__main__':
    socketio.run(debug=True)
