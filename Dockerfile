# Multi-stage Dockerfile for video generation system
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Remotion
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Install Remotion dependencies
RUN cd remotion && npm install

# Create workspace directory
RUN mkdir -p /workspace

# Expose port
EXPOSE 8000

# Default command (can be overridden)
CMD ["uvicorn", "src.api.main_db:app", "--host", "0.0.0.0", "--port", "8000"]
