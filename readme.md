# Selflearn Transkriptions-Backend

Ein Flask-basierter Webservice zur automatischen Transkription von Videos mittels OpenAI Whisper.

## Projektbeschreibung

Dieses Backend wurde im Rahmen einer Projektarbeit an der Universität Hildesheim entwickelt. Der Service ermöglicht die automatische Umwandlung von gesprochener Sprache in Videos zu Text (Speech-to-Text).

### Hauptfunktionen

- **Video-Download**: Herunterladen von Videos über URLs
- **Audio-Extraktion**: Extraktion der Tonspur aus Videos mittels FFmpeg
- **Transkription**: Spracherkennung mit OpenAI Whisper
- **Echtzeit-Kommunikation**: WebSocket-basierte Fortschrittsupdates via Flask-SocketIO
- **JWT-Authentifizierung**: Sichere API-Zugriffe

## Architektur

```
┌─────────────────┐     WebSocket      ┌─────────────────────────┐
│     Client      │◄──────────────────►│   Flask-SocketIO Server │
└─────────────────┘                    └───────────┬─────────────┘
                                                   │
                                       ┌───────────▼─────────────┐
                                       │    Background Worker    │
                                       │  ┌─────────────────────┐│
                                       │  │   Video Download    ││
                                       │  └──────────┬──────────┘│
                                       │  ┌──────────▼──────────┐│
                                       │  │  Audio Extraction   ││
                                       │  │      (FFmpeg)       ││
                                       │  └──────────┬──────────┘│
                                       │  ┌──────────▼──────────┐│
                                       │  │   Transcription     ││
                                       │  │     (Whisper)       ││
                                       │  └─────────────────────┘│
                                       └─────────────────────────┘
```

## Projektstruktur

```
ProjektArbeit/
├── app.py                  # Hauptanwendung mit Flask-SocketIO Server
├── config.py               # Zentrale Konfiguration
├── requirements.txt        # Python-Abhängigkeiten
├── Dockerfile              # Container-Konfiguration
├── .env.example            # Beispiel-Umgebungsvariablen
├── .env                    # Umgebungsvariablen (nicht im Repository)
├── utils/                  # Hilfsmodule
│   ├── __init__.py         # Paket-Initialisierung
│   ├── audio_extraction.py # FFmpeg Audio-Extraktion
│   ├── download_video.py   # Video-Download mit URL-Validierung
│   └── transcribe.py       # Whisper-Transkription
├── tests/                  # Unit- und Integrationstests
│   ├── test_transkription_route.py
│   └── videos/             # Test-Videos
└── model/                  # Whisper-Modell (optional)
```

## Technologie-Stack

| Komponente | Technologie | Version |
|------------|-------------|---------|
| Backend Framework | Flask | 3.0.x |
| WebSocket | Flask-SocketIO | 5.3.x |
| Speech-to-Text | OpenAI Whisper | latest |
| Audio-Verarbeitung | FFmpeg | 6.x |
| Authentifizierung | PyJWT | 2.x |
| WSGI Server | Gevent | 24.x |

## Konfiguration

Alle Laufzeitparameter werden über Umgebungsvariablen geladen und in `config.py` validiert. Die folgenden Schlüssel werden unterstützt und müssen in `.env` oder dem Container-Setup gesetzt werden:

| Variable | Pflicht | Default | Beschreibung |
|----------|---------|---------|--------------|
| `AUTH_SECRET_KEY` | ✅ | - | Shared Secret für JWT-Verifikation |
| `SAVE_SUBTITLE_ENDPOINT` | ✅ | - | REST-Endpoint zum Speichern der Untertitel |
| `WHISPER_MODEL` | ✅ | `small` | Whisper-Modell (`tiny`, `base`, `small`, `medium`, `large`) |
| `HOST` | ❌ | `0.0.0.0` | Bind-Adresse des Flask-Servers |
| `PORT` | ❌ | `5000` | Port des Flask-Servers |
| `DEBUG` | ❌ | `false` | Flask-Debug-Modus (`true`/`false`) |
| `DOWNLOAD_CHUNK_SIZE` | ❌ | `8192` | Chunk-Größe in Bytes beim Video-Download |
| `DOWNLOAD_TIMEOUT` | ❌ | `30` | Timeout in Sekunden für HTTP-Downloads |
| `LOG_LEVEL` | ❌ | `INFO` | Logging-Level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_FORMAT` | ❌ | siehe Code | Python-Logging-Format |

Die Methode `Config.validate()` stellt sicher, dass alle Pflichtwerte vor dem Serverstart gesetzt sind.


## Installation

### Voraussetzungen

- Python 3.9 oder höher
- FFmpeg (muss im System-PATH verfügbar sein)
- CUDA (optional, für GPU-Beschleunigung)

### Schritte

1. **Repository klonen**
   ```bash
   git clone <repository-url>
   cd ProjektArbeit
   ```

2. **Virtuelle Umgebung erstellen**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```

4. **Umgebungsvariablen konfigurieren**
   
   Kopieren Sie die Beispiel-Datei und passen Sie die Werte an:
   ```bash
   cp .env.example .env
   ```
   
   Bearbeiten Sie mindestens die Pflicht-Variablen in `.env`:
   ```env
   AUTH_SECRET_KEY=ihr-geheimer-schluessel
   SAVE_SUBTITLE_ENDPOINT=http://localhost:4200/api/subtitle/save_subtitle
   WHISPER_MODEL=small
   ```

5. **FFmpeg installieren**
   
   - **Windows**: [FFmpeg Download](https://ffmpeg.org/download.html) und zum PATH hinzufügen
   - **Linux**: `sudo apt install ffmpeg`
   - **macOS**: `brew install ffmpeg`

## Verwendung

### Server starten

```bash
python app.py
```

Der Server läuft standardmäßig auf `http://localhost:5000`.

### WebSocket-API

#### Event: `transcribe`

Startet eine neue Transkription.

**Request:**
```json
{
    "bearer_token": "jwt-token",
    "video_url": "https://example.com/video.mp4",
    "lessonId": "lesson-123",
    "realtime": true,
    "task_id": "custom-task-id"
}
```

**Events vom Server:**

| Event | Beschreibung | Payload |
|-------|--------------|---------|
| `task_started` | Task wurde gestartet | `{task_id, message}` |
| `progress` | Fortschrittsupdate | `{task_id, message}` |
| `complete` | Transkription abgeschlossen | `{task_id, transcription}` |
| `error` | Fehler aufgetreten | `{task_id, message}` |

### REST-Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/` | GET | Health-Check |
| `/health` | GET | Detaillierter Status |

## Tests

```bash
# Alle Tests ausführen
pytest

# Mit Coverage-Report
pytest --cov=. --cov-report=html

# Spezifische Tests
pytest tests/test_transkription_route.py -v
```

## Docker

### Image bauen

```bash
docker build -t selflearn-transcription-backend .
```

### Container starten

```bash
docker run -p 5000:5000 \
    -e AUTH_SECRET_KEY="your-secret-key" \
    -e SAVE_SUBTITLE_ENDPOINT="http://your-api/endpoint" \
    selflearn-transcription-backend
```

## Whisper-Modelle

Das Projekt verwendet das Whisper-Modell, das über die Umgebungsvariable `WHISPER_MODEL` in der `.env` oder im Container-Setup festgelegt wird. Verfügbare Modelle:

| Modell | Parameter | VRAM | Rel. Geschwindigkeit |
|--------|-----------|------|---------------------|
| tiny | 39 M | ~1 GB | ~32x |
| base | 74 M | ~1 GB | ~16x |
| small | 244 M | ~2 GB | ~6x |
| medium | 769 M | ~5 GB | ~2x |
| large | 1550 M | ~10 GB | 1x |

Um ein anderes Modell zu verwenden, passen Sie die Variable `WHISPER_MODEL` in Ihrer `.env` an, z.B.:
```env
WHISPER_MODEL=medium
```
Der Wert wird beim Start automatisch übernommen und in `config.py` validiert.

## Bekannte Einschränkungen

- FFmpeg muss separat installiert sein
- Große Videos benötigen entsprechend Speicherplatz
- GPU-Unterstützung erfordert CUDA-kompatible Hardware

## Autor

Lukas Dönges
- Universität: Universität Hildesheim
- Studiengang: Angewandte Informatik

---

*Erstellt im Rahmen der Projektarbeit im Dezember 2025*
