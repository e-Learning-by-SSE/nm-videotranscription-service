import time

from flask import Flask
from flask_openapi3 import OpenAPI, Info
from flask_socketio import SocketIO, emit

from routes.routes import transcripe_blueprint
from services.transcription_service import transcribe_audio_from_url

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

app.register_blueprint(transcripe_blueprint)


@socketio.on('transcribe')
def handle_transcription(data):
    video_url = data.get('video_url')

    if not video_url:
        emit('error', {'message': 'Video URL is required'})
        return

    emit('progress', {'message': 'Starting transcription service ...'})

    transcription = transcribe_audio_from_url(video_url)

    emit('complete', {'transcription': transcription})



if __name__ == '__main__':
    socketio.run(debug=True)
