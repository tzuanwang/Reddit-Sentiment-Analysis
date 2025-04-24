FROM apache/airflow:2.5.1-python3.9

USER root
RUN pip install --no-cache-dir torch transformers psycopg2-binary

USER airflow
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dags/ /opt/airflow/dags/
