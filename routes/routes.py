from flask import Blueprint, request, jsonify
from services.transcription_service import transcribe_audio

routes_bp = Blueprint('routes', __name__)



@routes_bp.route('/transcribe', methods=['POST'])
def transcribe():
    # Assume the request contains a file
    file = request.files['file']
    # Process file and transcribe
    transcription = transcribe_audio(file)
    return jsonify({"transcription": transcription})