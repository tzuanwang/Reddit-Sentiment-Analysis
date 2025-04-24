# airflow/dags/sentiment_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from backend.app.reddit_client import fetch_subreddit_data
from transformers import pipeline
from backend.app.db import SessionLocal
from backend.app.models import Prediction, Post

default_args = {
    "owner": "airflow",
    "start_date": datetime(2025, 4, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

def predict_emotions(**kwargs):
    pipe = pipeline("text-classification", model="bhadresh-savani/albert-base-v2-emotion")
    session = SessionLocal()
    posts = session.query(Post).all()
    for post in posts:
        res = pipe(post.title[:512])[0]
        pred = Prediction(
            post_id=post.id,
            emotion=res["label"],
            score=res["score"],
            created_utc=int(datetime.utcnow().timestamp())
        )
        session.add(pred)
    session.commit()
    session.close()

with DAG(
    "reddit_sentiment_shift",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False
) as dag:

    t1 = PythonOperator(
        task_id="fetch_reddit",
        python_callable=fetch_subreddit_data,
        op_kwargs={"subreddit_name": "example_subreddit", "limit": 100}
    )
    t2 = PythonOperator(
        task_id="predict_emotion",
        python_callable=predict_emotions
    )

    t1 >> t2
