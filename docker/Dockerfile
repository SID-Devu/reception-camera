FROM python:3.11-slim

WORKDIR /opt/reception-camera

# System deps for OpenCV, audio, GStreamer
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxrender-dev libxext6 \
    espeak espeak-data alsa-utils \
    libgstreamer1.0-0 gstreamer1.0-plugins-good gstreamer1.0-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY tools/ ./tools/
COPY models/ ./models/

# Create data directories
RUN mkdir -p data/db data/embeddings data/logs data/faces

EXPOSE 8000

CMD ["python", "app/main.py"]