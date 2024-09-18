from app import app


def test_transkription_route():
    client = app.test_client()
    response = client.post('/transcribe', data={"file": open('video.mp4', 'rb')})
    assert response.status_code == 200
    print(response.json)


def test_transkrip_download_route():
    client = app.test_client()
    response = client.post('/transcribe/download', json={"video_url": "https://staging.sse.uni-hildesheim.de:9006/upload/ung7m79i-Java%20010%20-%20Motivation.mp4"})
    assert response.status_code == 200
    print(response.json)