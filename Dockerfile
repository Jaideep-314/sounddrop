FROM python:3.12-slim

# Install system dependencies: ffmpeg, nodejs (needed for yt-dlp JS player decryption), ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -U -r requirements.txt

# Copy backend files
COPY server.py index.html ./

ENV PORT=10000
EXPOSE 10000

CMD ["python", "server.py"]
