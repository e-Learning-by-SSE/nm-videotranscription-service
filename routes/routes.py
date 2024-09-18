from flask import Blueprint, request, jsonify
from services.transcription_service import transcribe_audio, transcribe_audio_from_url
from flask_openapi3 import Tag, FileStorage
from pydantic import BaseModel, Field

transcripe_blueprint = Blueprint('transcribe', __name__)
transcribe_tag = Tag(name='transcribe', description='Operations related to transcriptions')

class UploadFileForm(BaseModel):
    file: FileStorage
    file_type: str = Field(None, description="File Type")

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
