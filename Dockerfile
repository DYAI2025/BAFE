FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    wget \
    curl \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set Python environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Download Swiss Ephemeris files FIRST (before pyproject.toml)
RUN mkdir -p /usr/local/share/swisseph && \
    wget --timeout=60 -O /usr/local/share/swisseph/sepl_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/sepl_18.se1 && \
    wget --timeout=60 -O /usr/local/share/swisseph/semo_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/semo_18.se1 && \
    wget --timeout=60 -O /usr/local/share/swisseph/seas_18.se1 https://github.com/aloistr/swisseph/raw/master/ephe/seas_18.se1 && \
    wget --timeout=60 -O /usr/local/share/swisseph/seplm06.se1 https://github.com/aloistr/swisseph/raw/master/ephe/seplm06.se1 && \
    chmod -R 755 /usr/local/share/swisseph

# Set ephemeris path
ENV SE_EPHE_PATH=/usr/local/share/swisseph

# Copy and install Python package
COPY pyproject.toml .
COPY bazi_engine/ ./bazi_engine/
COPY spec/ ./spec/

# Install dependencies directly (without editable install)
RUN pip install --upgrade pip setuptools wheel && \
    pip install pyswisseph>=2.10.3 fastapi>=0.109.0 uvicorn[standard]>=0.27.0 jsonschema>=4.20.0

# Install the package itself
RUN pip install --no-deps -e .

# Expose port
EXPOSE 8080

# Start with dynamic PORT support for Railway/Fly.io
CMD ["sh", "-c", "uvicorn bazi_engine.app:app --host 0.0.0.0 --port ${PORT:-8080} --log-level info"]
