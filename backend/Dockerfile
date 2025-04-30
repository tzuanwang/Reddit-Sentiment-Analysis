FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for spacy
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies with specific approach to avoid compilation issues
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir wheel setuptools && \
    # Install spaCy separately first
    pip install --no-cache-dir spacy>=3.2.0 && \
    # Then download the model
    python -m spacy download en_core_web_md && \
    # Then install remaining requirements
    pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "app.main:app", "--bind", "0.0.0.0:5000", "--workers", "2"]