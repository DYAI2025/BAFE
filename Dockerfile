FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for compiling pyswisseph
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir .

# Copy source code
COPY bazi_engine/ ./bazi_engine/

# Expose port
EXPOSE 8080

# Run the application
ENV PORT=8080
CMD ["sh", "-c", "uvicorn bazi_engine.app:app --host 0.0.0.0 --port ${PORT}"]
