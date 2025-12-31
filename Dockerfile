# =============================================================================
# Selflearn Transkriptions-Backend - Dockerfile
# =============================================================================
# Autor: Lukas Dönges
# Datum: Dezember 2025
# =============================================================================

FROM python:3.9-slim-bullseye AS base

# Metadaten
LABEL description="Selflearn Transkriptions-Backend mit OpenAI Whisper"
LABEL version="1.0.0"

# Umgebungsvariablen
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Arbeitsverzeichnis setzen
WORKDIR /app

# System-Abhängigkeiten installieren
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python-Abhängigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungscode kopieren
COPY . .

# Nicht-root Benutzer erstellen für Sicherheit
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Port freigeben
EXPOSE 5000

# Health-Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

# Anwendung starten
CMD ["python", "app.py"]
