FROM python:3.12-slim

# Install system dependencies: ffmpeg, nodejs, ca-certificates, curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install pre-release/nightly yt-dlp with full EJS engine for latest YouTube player extraction
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -U --pre "yt-dlp[default]" yt-dlp-ejs && \
    pip install --no-cache-dir -U -r requirements.txt

# Copy source code
COPY server.py index.html ./

ENV PORT=10000
EXPOSE 10000

CMD ["python", "server.py"]
