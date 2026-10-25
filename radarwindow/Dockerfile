# Python 3.12 — stable pydantic-core wheels. Do not upgrade to 3.13+ without testing.
FROM python:3.12-slim

WORKDIR /app

# ffmpeg for reel composition; ca-certificates for httpx
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Pipeline package (radarwindow) + web backend deps in one image —
# a single Railway service serves the API and runs the crons in-process
# (web/backend/app/scheduler.py, enabled via RUN_SCHEDULER=1).
COPY pyproject.toml ./
COPY src/ ./src/
COPY web/backend/requirements.txt ./web-requirements.txt
RUN pip install --no-cache-dir . && \
    pip install --no-cache-dir -r web-requirements.txt

COPY web/backend/ ./web/backend/

# Railway mounts /data as a volume; media assets live here
RUN mkdir -p /data/media

WORKDIR /app/web/backend
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
