from utils.file_manager import save_file_temporarily
from utils.audio_extraction import extract_audio
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