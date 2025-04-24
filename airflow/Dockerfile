# 1. Start from the official Airflow image
FROM apache/airflow:2.5.1-python3.9

# 2. Switch to root only for OS-level package installs (if needed)
USER root
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
      gcc \
      libpq-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# 3. Copy your Python dependency list
COPY requirements.txt /requirements.txt

# 4. Switch to the airflow user for pip installs
USER airflow
RUN pip install --no-cache-dir -r /requirements.txt

# 5. Copy over your DAG definitions
COPY dags/ /opt/airflow/dags/

# 6. Ensure the entrypoint & default cmd stay as in the base image
USER airflow
