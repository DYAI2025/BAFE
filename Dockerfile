FROM python:3.11-slim
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*
# Download Swiss Ephemeris files
RUN mkdir -p /app/ephe && \
    wget -q -O /app/ephe/sepl_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/sepl_18.se1 && \
    wget -q -O /app/ephe/semo_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/semo_18.se1 && \
    wget -q -O /app/ephe/seas_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/seas_18.se1 && \
    wget -q -O /app/ephe/seplm06.se1 https://github.com/aloistr/swisseph/raw/master/ephe/seplm06.se1 && \
    chmod -R 755 /app/ephe
# Set environment
ENV SE_EPHE_PATH=/app/ephe
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
# Copy dependency spec first for Docker layer caching
COPY pyproject.toml .
# Copy source code (needed for pip install)
COPY bazi_engine/ ./bazi_engine/
# Install package (non-editable for production)
RUN pip install --no-cache-dir .
# Test ephemeris files
COPY test_ephe.py .
RUN python test_ephe.py
# Expose port
EXPOSE 8080
# Start mit uvicorn direkt
CMD ["uvicorn", "bazi_engine.app:app", "--host", "0.0.0.0", "--port", "8080"]
