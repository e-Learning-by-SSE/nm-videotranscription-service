import re
import subprocess
import tempfile



def extract_audio(video_file_path, socketio, client_sid):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
        audio_file_path = temp_audio.name  # Get the temp file path

        print(f"Extracting audio from {video_file_path} to {audio_file_path}")

        duration_command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                            'default=noprint_wrappers=1:nokey=1', video_file_path]
        duration_output = subprocess.check_output(duration_command).decode('utf-8')
        duration = float(duration_output.strip())

        command = [
            'ffmpeg',
            '-y',  # Overwrite output files without asking
            '-i', video_file_path,  # Input file path
            '-vn',  # Disable video processing
            '-acodec', 'libmp3lame',  # Copy the audio stream without reencoding
            audio_file_path  # Output file path
        ]
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       universal_newlines=True)
            time_regex = re.compile(r'(\d+):(\d+):(\d+\.\d+)')

            for line in process.stdout:
                # Match the line to the regex
                match = time_regex.search(line)
                if match:
                    hours, minutes, seconds = map(float, match.groups())
                    current_time = hours * 3600 + minutes * 60 + seconds
                    percent = (current_time / duration) * 100
                    print(f"Extracting audio... {percent}%")
                    socketio.emit('progress', {'message': f'Extracting audio... {percent}%'}, to=client_sid)

            print(f"Audio extracted successfully to {audio_file_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error extracting audio: {e}")

        return audio_file_path





