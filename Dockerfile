FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# libpq-dev and gcc are often needed for psycopg2, though we use binary here for speed.
# curl for healthchecks if needed.
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set python path to current dir to allow module imports
ENV PYTHONPATH=/app

# Default command runs the service demonstration
CMD ["python", "-m", "src.search_service"]
