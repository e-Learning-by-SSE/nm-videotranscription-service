


def transcribe_audio_with_progress(model, audio_file_path):
    result = model.transcribe(audio_file_path)

    return result