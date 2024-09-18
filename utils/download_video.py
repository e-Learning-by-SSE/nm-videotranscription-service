import requests

def download_video(video_url, save_path):
    response = requests.get(video_url)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
    else:
        raise Exception("Failed to download video")