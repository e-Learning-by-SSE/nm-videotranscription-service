from utils.download_video import download_video
from utils.file_manager import save_file_temporarily
import os
from utils.audio_extraction import extract_audio
import tempfile
import whisper

def transcribe_audio(video_file):

    print("Transcribing audio...")

    video_file_path = save_file_temporarily(video_file)
    print("File saved temporarily")
    audio_file_path = extract_audio(video_file_path)
    print("Audio extracted")
    model = whisper.load_model("small")
    print("Model loaded")
    transcription = model.transcribe(audio_file_path)

    return transcription

async def transcribe_audio_from_url(video_url):
    with tempfile.TemporaryDirectory() as tmpdirname:
        video_file_path = os.path.join(tmpdirname, "temp_video.mp4")

        print("Downloading video...")
        await download_video(video_url, video_file_path)
        print("Video downloaded and saved temporarily")

        print("Extracting audio...")
        audio_file_path = extract_audio(video_file_path)
        print("Audio extracted")

        # Load Whisper model and transcribe audio
        print("Loading Whisper model...")
        model = whisper.load_model("small")
        print("Model loaded")

        print("Transcribing audio...")
        transcription = model.transcribe(audio_file_path)
        return transcription