FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies required by MediaPipe (libGLESv2, libEGL) and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgles2 \
    libegl1 \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r ./backend/requirements.txt

# Copy application source code
COPY . .

# Expose Render default port
ENV PORT=10000
EXPOSE 10000

# Start Uvicorn web server
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
