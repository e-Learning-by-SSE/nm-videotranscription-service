from flask_socketio import emit

from utils.download_video import download_video
from utils.file_manager import save_file_temporarily
import os
from utils.audio_extraction import extract_audio
import tempfile
import whisper

from utils.transcribe import transcribe_audio_with_progress


def transcribe_audio_from_url(video_url):
    with tempfile.TemporaryDirectory() as tmpdirname:
        video_file_path = os.path.join(tmpdirname, "temp_video.mp4")

        emit('progress', {'message': 'Downloading video...'})
        download_video(video_url, video_file_path)

        emit('progress', {'message': 'Extracting audio...'})
        audio_file_path = extract_audio(video_file_path)

        emit('progress', {'message': 'Loading model...'})
        model = whisper.load_model("small")

        emit('progress', {'message': 'Transcribing audio...'})
        transcription = transcribe_audio_with_progress(model, audio_file_path)
        return transcription