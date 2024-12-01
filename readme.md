# Selflearn Transkriptions Backend

## Description
This project is a backend service for self-learning transcription. It extracts audio from video files and processes it for transcription purposes. The backend is built using Python and Flask, and it utilizes Flask-SocketIO for real-time communication.

## Installation
To install the project dependencies, run the following command:

```bash
pip install -r requirements.txt
```

## Usage
To start the backend server, run the following command:

```bash
python app.py
```

## Testing
To run the tests, use the following command:

```bash
pytest
```

## Docker
To build and run the Docker container, use the following commands:

```bash
docker build -t selflearn-transkriptions-backend .
docker run -p 80:80 selflearn-transkriptions-backend
```

## License
This project is licensed under the MIT License. See the `LICENSE` file for more details.
