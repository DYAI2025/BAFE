FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for compiling pyswisseph
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir .

# Download Swiss Ephemeris files
RUN mkdir -p /usr/local/share/swisseph && \
    wget -O /usr/local/share/swisseph/sepl_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/sepl_18.se1 && \
    wget -O /usr/local/share/swisseph/semo_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/semo_18.se1 && \
    wget -O /usr/local/share/swisseph/seas_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/seas_18.se1 && \
    wget -O /usr/local/share/swisseph/seplm06.se1 https://github.com/aloistr/swisseph/raw/master/ephe/seplm06.se1 && \
    chmod -R 755 /usr/local/share/swisseph

# Set environment variable for pyswisseph
ENV SE_EPHE_PATH=/usr/local/share/swisseph

# Copy source code
COPY bazi_engine/ ./bazi_engine/

# Install dependencies
RUN pip install --no-cache-dir .

# Expose port
EXPOSE 8080

# Run the application
ENV PORT=8080
CMD ["sh", "-c", "uvicorn bazi_engine.app:app --host 0.0.0.0 --port ${PORT}"]
