
import subprocess
import tempfile


def extract_audio(video_file_path):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
        audio_file_path = temp_audio.name  # Get the temp file path

        print(f"Extracting audio from {video_file_path} to {audio_file_path}")

        command = [
            'ffmpeg',
            '-y',  # Overwrite output files without asking
            '-i', video_file_path,  # Input file path
            '-vn',  # Disable video processing
            '-acodec', 'libmp3lame',  # Copy the audio stream without reencoding
            audio_file_path  # Output file path
        ]
        try:
            subprocess.run(command, check=True)
            print(f"Audio extracted successfully to {audio_file_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error extracting audio: {e}")

        return audio_file_path





