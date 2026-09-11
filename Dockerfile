# Multi-stage lightweight Dockerfile for Render deployment
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Install system dependencies including FFmpeg and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-noto-core \
    fonts-liberation \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Pre-download required fonts
RUN python -m src.font_manager

# Ensure runtime directories exist
RUN mkdir -p assets/videos/cache data/quran_cache output

EXPOSE 8080

# Run FastAPI healthcheck server with embedded Telegram Bot worker
CMD ["python", "server.py"]
