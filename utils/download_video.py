import requests
from flask_socketio import emit


def download_video(video_url, save_path, socketio, client_sid):
    response = requests.get(video_url, stream=True)
    total_length = int(response.headers.get('content-length'))

    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = int(downloaded / total_length * 100)
                    socketio.emit('progress', {'message': f'Downloading video... {percent}%'}, to=client_sid)
    else:
        raise Exception("Failed to download video")