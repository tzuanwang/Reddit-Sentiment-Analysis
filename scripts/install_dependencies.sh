# 1. Start from the official Airflow image
FROM apache/airflow:2.5.1-python3.9

# 2. Switch to root only for OS-level package installs
USER root
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
      gcc \
      g++ \
      libpq-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# 3. Copy your Python dependency list
COPY requirements.txt /requirements.txt

# 4. Switch to the airflow user for pip installs
USER airflow

# Install dependencies with specific approach to avoid compilation issues
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir wheel setuptools && \
    # Install spaCy separately first
    pip install --no-cache-dir spacy>=3.2.0 && \
    # Then download the medium model to save space
    python -m spacy download en_core_web_md && \
    # Then install remaining requirements
    pip install --no-cache-dir -r /requirements.txt && \
    # Download NLTK data
    python -c "import nltk; nltk.download('vader_lexicon')"

# 5. Copy over your DAG definitions
COPY dags/ /opt/airflow/dags/

# 6. Ensure the entrypoint & default cmd stay as in the base image
USER airflow