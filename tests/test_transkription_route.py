from app import app


def test_transkription_route():
    client = app.test_client()
    response = client.post('/transcribe', data={"file": open('video.mp4', 'rb')})
    assert response.status_code == 200
    print(response.json)

