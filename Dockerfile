FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    MALLOC_ARENA_MAX=2 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    TF_ENABLE_ONEDNN_OPTS=0

# Install system dependencies required by MediaPipe (libGLESv2, libEGL) and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgles2 \
    libegl1 \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install lightweight CPU-only PyTorch first (saves ~3GB of CUDA/NVIDIA memory overhead)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies (excluding torch which is already installed as CPU-only)
COPY backend/requirements.txt ./backend/requirements.txt
RUN grep -v "^torch" ./backend/requirements.txt > ./backend/requirements-notorch.txt && \
    pip install --no-cache-dir -r ./backend/requirements-notorch.txt

# Copy application source code
COPY . .

# Expose Render default port
ENV PORT=10000
EXPOSE 10000

# Start Uvicorn web server
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
