# Selflearn Transkriptions Backend

## Description
This project is a backend service for self-learning transcription. It extracts audio from video files and processes it for transcription purposes. The backend is built using Python and Flask, and it utilizes Flask-SocketIO for real-time communication.

## Environment Variables
The following environment variables must be set for the application to function correctly:

- `SAVE_SUBTITLE_ENDPOINT`: Endpoint to save subtitles. Example:
  ```
  SAVE_SUBTITLE_ENDPOINT=http://localhost:4200/api/subtitle/save_subtitle
  ```
- `AUTH_SECRET_KEY`: Secret key for authentication. Example:
  ```
  AUTH_SECRET_KEY="1a1alhi05+wZcfAaPA8R2GTM5ay2xUMsr/DKJJkS6Fw="
  ```

Ensure these variables are configured correctly in your environment or a `.env` file.

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

