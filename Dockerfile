# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TOKENIZERS_PARALLELISM=false

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download HuggingFace models during build
COPY download_models.py .
RUN python download_models.py

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Run the application with 2 workers, 2 threads, and preload for CoW memory sharing
CMD ["gunicorn", "AIAscentBackend.wsgi:application", "--bind=0.0.0.0:8000", "--workers=3", "--threads=2", "--worker-class=gthread", "--preload", "--timeout=600"]