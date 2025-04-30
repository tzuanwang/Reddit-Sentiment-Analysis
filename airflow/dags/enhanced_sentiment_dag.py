# airflow/dags/enhanced_sentiment_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import time
import logging

from backend.app.reddit_client import fetch_subreddit_data
from backend.app.sentiment_analyzer import analyze_text
from backend.app.db import SessionLocal
from backend.app.models import (
    Post, Comment, Prediction, PostSentiment, CommentSentiment
)

default_args = {
    "owner": "airflow",
    "start_date": datetime(2025, 4, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

def predict_emotions(**kwargs):
    """Legacy emotion prediction task - keeping for backward compatibility"""
    from transformers import pipeline
    pipe = pipeline("text-classification", model="bhadresh-savani/albert-base-v2-emotion")
    session = SessionLocal()
    posts = session.query(Post).all()
    for post in posts:
        try:
            res = pipe(post.title[:512])[0]
            pred = Prediction(
                post_id=post.id,
                emotion=res["label"],
                score=res["score"],
                created_utc=int(datetime.utcnow().timestamp())
            )
            session.add(pred)
        except Exception as e:
            logging.error(f"Error processing post {post.id}: {str(e)}")
    session.commit()
    session.close()

def analyze_posts(**kwargs):
    """Analyze post titles with advanced sentiment analysis"""
    session = SessionLocal()
    current_time = int(datetime.utcnow().timestamp())
    
    # Get posts that haven't been analyzed yet
    posts = session.query(Post).outerjoin(
        PostSentiment
    ).filter(
        PostSentiment.id == None
    ).all()
    
    logging.info(f"Found {len(posts)} posts to analyze")
    
    for post in posts:
        try:
            # Analyze the post title
            analysis_results = analyze_text(post.title)
            
            # Get highest scoring categories
            sentiment_category = max(
                analysis_results.get("sentiment", {}).items(), 
                key=lambda x: x[1] if x[1] is not None else 0,
                default=("unknown", 0)
            )[0]
            
            emotion_category = max(
                analysis_results.get("emotion", {}).items(), 
                key=lambda x: x[1] if x[1] is not None else 0,
                default=("unknown", 0)
            )[0]
            
            hate_category = max(
                analysis_results.get("hate_speech", {}).items(), 
                key=lambda x: x[1] if x[1] is not None else 0,
                default=("unknown", 0)
            )[0]
            
            # Create sentiment record
            post_sentiment = PostSentiment(
                post_id=post.id,
                clean_text=analysis_results["cleaned"]["clean"],
                lemma_text=analysis_results["cleaned"]["lemma"],
                char_count=analysis_results["cleaned"]["char_count"],
                word_count=analysis_results["cleaned"]["word_count"],
                sentiment_scores=analysis_results["sentiment"],
                emotion_scores=analysis_results["emotion"],
                hate_speech_scores=analysis_results["hate_speech"],
                normalized_sentiment=analysis_results["normalized_sentiment"],
                normalized_emotion=analysis_results["normalized_emotion"],
                normalized_hate_speech=analysis_results["normalized_hate_speech"],
                top_sentiment=sentiment_category,
                top_emotion=emotion_category,
                top_hate_category=hate_category,
                created_utc=post.created_utc,
                analyzed_utc=current_time
            )
            
            session.add(post_sentiment)
            
            # Commit every 10 posts to avoid large transactions
            if posts.index(post) % 10 == 0:
                session.commit()
                
        except Exception as e:
            logging.error(f"Error analyzing post {post.id}: {str(e)}")
    
    session.commit()
    session.close()

def analyze_comments(**kwargs):
    """Analyze comments with advanced sentiment analysis"""
    session = SessionLocal()
    current_time = int(datetime.utcnow().timestamp())
    
    # Get comments that haven't been analyzed yet (in batches)
    batch_size = 100
    offset = 0
    
    while True:
        comments = session.query(Comment).outerjoin(
            CommentSentiment
        ).filter(
            CommentSentiment.id == None
        ).order_by(Comment.created_utc.desc()).limit(batch_size).offset(offset).all()
        
        if not comments:
            break
            
        logging.info(f"Processing batch of {len(comments)} comments")
        
        for comment in comments:
            try:
                # Analyze the comment body
                analysis_results = analyze_text(comment.body)
                
                # Get highest scoring categories
                sentiment_category = max(
                    analysis_results.get("sentiment", {}).items(), 
                    key=lambda x: x[1] if x[1] is not None else 0,
                    default=("unknown", 0)
                )[0]
                
                emotion_category = max(
                    analysis_results.get("emotion", {}).items(), 
                    key=lambda x: x[1] if x[1] is not None else 0,
                    default=("unknown", 0)
                )[0]
                
                hate_category = max(
                    analysis_results.get("hate_speech", {}).items(), 
                    key=lambda x: x[1] if x[1] is not None else 0,
                    default=("unknown", 0)
                )[0]
                
                # Create sentiment record
                comment_sentiment = CommentSentiment(
                    comment_id=comment.id,
                    clean_text=analysis_results["cleaned"]["clean"],
                    lemma_text=analysis_results["cleaned"]["lemma"],
                    char_count=analysis_results["cleaned"]["char_count"],
                    word_count=analysis_results["cleaned"]["word_count"],
                    sentiment_scores=analysis_results["sentiment"],
                    emotion_scores=analysis_results["emotion"],
                    hate_speech_scores=analysis_results["hate_speech"],
                    normalized_sentiment=analysis_results["normalized_sentiment"],
                    normalized_emotion=analysis_results["normalized_emotion"],
                    normalized_hate_speech=analysis_results["normalized_hate_speech"],
                    top_sentiment=sentiment_category,
                    top_emotion=emotion_category,
                    top_hate_category=hate_category,
                    created_utc=comment.created_utc,
                    analyzed_utc=current_time
                )
                
                session.add(comment_sentiment)
                
                # Commit every 10 comments to avoid large transactions
                if comments.index(comment) % 10 == 0:
                    session.commit()
                    
            except Exception as e:
                logging.error(f"Error analyzing comment {comment.id}: {str(e)}")
        
        session.commit()
        
        # Move to next batch
        offset += batch_size
        
        # Add a small delay to prevent overwhelming the database
        time.sleep(1)
    
    session.close()

with DAG(
    "enhanced_reddit_sentiment",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False
) as dag:

    t1 = PythonOperator(
        task_id="fetch_reddit",
        python_callable=fetch_subreddit_data,
        op_kwargs={"subreddit_name": "CryptoCurrency", "limit": 100}
    )
    
    t2 = PythonOperator(
        task_id="predict_emotion_legacy",
        python_callable=predict_emotions
    )
    
    t3 = PythonOperator(
        task_id="analyze_posts",
        python_callable=analyze_posts
    )
    
    t4 = PythonOperator(
        task_id="analyze_comments",
        python_callable=analyze_comments
    )

    # Define the workflow
    t1 >> [t2, t3] >> t4