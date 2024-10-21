from flask import Blueprint, request, jsonify
from services.transcription_service import transcribe_audio, transcribe_audio_from_url

transcripe_blueprint = Blueprint('transcribe', __name__)

@transcripe_blueprint.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        # Assume the request contains a file
        file = request.files['file']
        # Process file and transcribe
        transcription = transcribe_audio(file)
        return jsonify({"transcription": transcription})
    except Exception as e:
        return jsonify({"error": str(e)})

@transcripe_blueprint.route('/transcribe/download', methods=['POST'])
def transcribe_downloadFromURL():
        try:
            video_url = request.json['video_url']
            # Process file and transcribe
            transcription = transcribe_audio_from_url(video_url)
            return jsonify({"transcription": transcription})
        except Exception as e:
            return jsonify({"error": e})
