FROM python:3.11-slim

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (split heavy packages for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir numpy==1.26.3 && \
    pip install --no-cache-dir opencv-python-headless==4.9.0.80 && \
    pip install --no-cache-dir mediapipe==0.10.14 && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
