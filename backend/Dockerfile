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

# Install dependencies with improved approach
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir wheel setuptools && \
    # Install packages in a specific order to avoid conflicts
    pip install --no-cache-dir --prefer-binary numpy==1.24.3 && \
    pip install --no-cache-dir --prefer-binary spacy==3.5.3 && \
    # Download the language model
    python -m spacy download en_core_web_md && \
    # Install remaining requirements
    pip install --no-cache-dir --prefer-binary -r requirements.txt && \
    # Download NLTK data
    python -c "import nltk; nltk.download('vader_lexicon')"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2"]