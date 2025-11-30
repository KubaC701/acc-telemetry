# Use Python 3.10 slim image
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# tesseract-ocr: for OCR
# libgl1: for OpenCV
# ffmpeg: for video processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    libgl1 \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a non-root user and switch to it (security best practice for HF Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Create directories for data if they don't exist (and set permissions)
# Note: In HF Spaces, we might need to ensure these are writable
# We'll rely on the app creating them, but since we are non-root, 
# we need to make sure the workdir is owned by user or writable.
# For simplicity in this setup, we'll assume the app writes to ./videos 
# which we copied. Let's make sure the user owns /app
USER root
RUN chown -R user:user /app
USER user

# Expose the port (Hugging Face Spaces expects 7860)
EXPOSE 7860

# Command to run the application
CMD ["uvicorn", "src.web.main:app", "--host", "0.0.0.0", "--port", "7860"]
