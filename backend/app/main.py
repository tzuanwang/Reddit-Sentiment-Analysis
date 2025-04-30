# backend/app/main.py
from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Optional, List
import time
import os

from .db import SessionLocal, engine
from .models import Base, Post, Comment, PostSentiment, CommentSentiment
from .reddit_client import fetch_subreddit_data
from .sentiment_analyzer import analyze_text

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Reddit Sentiment Analysis API")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/debug")
def debug_endpoint():
    """Simple endpoint for debugging connectivity"""
    return {"status": "ok", "message": "Backend is reachable"}

@app.post("/harvest/{subreddit}")
def harvest(subreddit: str, limit: int = Query(100, ge=1, le=500)):
    """Harvest posts and comments from a subreddit and automatically analyze them"""
    try:
        # Harvest the posts
        posts = fetch_subreddit_data(subreddit, limit=limit)
        
        # Analyze each post right after harvesting
        db = SessionLocal()
        analyzed_count = 0
        try:
            for post in posts:
                try:
                    # analyze_post handles all three types of analysis
                    result = analyze_post(post.id, db)
                    analyzed_count += 1
                    print(f"Analyzed post {post.id}: sentiment={result['sentiment']}, emotion={result['emotion']}")
                except Exception as e:
                    print(f"Error analyzing post {post.id}: {str(e)}")
        finally:
            db.close()
        
        return {
            "harvested": len(posts), 
            "subreddit": subreddit, 
            "analyzed": analyzed_count,
            "message": f"Successfully harvested and analyzed {analyzed_count} posts from r/{subreddit}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/analyze/text")
def analyze_single_text(text: str):
    """Analyze a single text with all sentiment models"""
    try:
        results = analyze_text(text)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/posts")
def get_posts(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[int] = None,
    end_date: Optional[int] = None,
    sentiment: Optional[str] = None,
    emotion: Optional[str] = None
):
    """Get posts with optional filtering"""
    query = db.query(Post).join(PostSentiment)
    
    # Apply filters
    if start_date:
        query = query.filter(Post.created_utc >= start_date)
    if end_date:
        query = query.filter(Post.created_utc <= end_date)
    if sentiment:
        query = query.filter(PostSentiment.top_sentiment == sentiment)
    if emotion:
        query = query.filter(PostSentiment.top_emotion == emotion)
    
    # Execute query with pagination
    total = query.count()
    posts = query.order_by(Post.created_utc.desc()).offset(skip).limit(limit).all()
    
    # Format response
    return {
        "total": total,
        "posts": [
            {
                "id": post.id,
                "title": post.title,
                "created_utc": post.created_utc,
                "sentiment": post.sentiment_analysis.top_sentiment if post.sentiment_analysis else None,
                "emotion": post.sentiment_analysis.top_emotion if post.sentiment_analysis else None
            }
            for post in posts
        ]
    }

@app.get("/posts/{post_id}")
def get_post_details(post_id: str, db: Session = Depends(get_db)):
    """Get detailed info about a specific post"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Get sentiment data if available
    sentiment = db.query(PostSentiment).filter(PostSentiment.post_id == post_id).first()
    
    # Get comments
    comments = db.query(Comment).filter(Comment.post_id == post_id).all()
    comment_sentiments = {
        cs.comment_id: cs 
        for cs in db.query(CommentSentiment).filter(
            CommentSentiment.comment_id.in_([c.id for c in comments])
        ).all()
    }
    
    # Format response
    return {
        "post": {
            "id": post.id,
            "title": post.title,
            "created_utc": post.created_utc,
        },
        "sentiment": {
            "clean_text": sentiment.clean_text if sentiment else None,
            "sentiment_scores": sentiment.sentiment_scores if sentiment else {},
            "emotion_scores": sentiment.emotion_scores if sentiment else {},
            "hate_speech_scores": sentiment.hate_speech_scores if sentiment else {},
            "top_sentiment": sentiment.top_sentiment if sentiment else None,
            "top_emotion": sentiment.top_emotion if sentiment else None,
            "top_hate_category": sentiment.top_hate_category if sentiment else None,
        },
        "comments": [
            {
                "id": comment.id,
                "body": comment.body,
                "created_utc": comment.created_utc,
                "sentiment": comment_sentiments.get(comment.id).top_sentiment if comment.id in comment_sentiments else None,
                "emotion": comment_sentiments.get(comment.id).top_emotion if comment.id in comment_sentiments else None,
            }
            for comment in comments
        ]
    }

@app.get("/stats/sentiment")
def get_sentiment_stats(
    db: Session = Depends(get_db),
    start_date: Optional[int] = None,
    end_date: Optional[int] = None,
    group_by: str = Query("day", regex="^(hour|day|week|month)$")
):
    """Get sentiment statistics aggregated by time period"""
    try:
        # SQL for time grouping based on the selected period
        time_group = {
            "hour": "date_trunc('hour', to_timestamp(ps.created_utc))",
            "day": "date_trunc('day', to_timestamp(ps.created_utc))",
            "week": "date_trunc('week', to_timestamp(ps.created_utc))",
            "month": "date_trunc('month', to_timestamp(ps.created_utc))",
        }[group_by]
        
        # Build the SQL query
        query_str = f"""
        SELECT 
            {time_group} AS time_period,
            ps.top_sentiment AS sentiment,
            COUNT(*) AS count
        FROM 
            post_sentiments ps
        """
        
        # Add filters
        conditions = []
        params = {}
        
        if start_date:
            conditions.append("ps.created_utc >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            conditions.append("ps.created_utc <= :end_date")
            params["end_date"] = end_date
        
        if conditions:
            query_str += " WHERE " + " AND ".join(conditions)
        
        # Add grouping and ordering
        query_str += """
        GROUP BY 
            time_period, ps.top_sentiment
        ORDER BY 
            time_period, ps.top_sentiment
        """
        
        # Create a text object from the query string
        query = text(query_str)
        
        # Execute the query
        result = db.execute(query, params).fetchall()
        
        # Format the results
        formatted = {}
        for row in result:
            time_str = row[0].isoformat()
            sentiment = row[1]
            count = row[2]
            
            if time_str not in formatted:
                formatted[time_str] = {}
            
            formatted[time_str][sentiment] = count
        
        return formatted
        
    except Exception as e:
        print(f"Error in sentiment stats: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching sentiment stats: {str(e)}")

@app.get("/examples/{category_type}/{category}")
def get_examples(
    category_type: str,
    category: str,
    db: Session = Depends(get_db),
    limit: int = Query(5, ge=1, le=20)
):
    """Get example posts/comments for a specific sentiment/emotion category"""
    if category_type not in ["sentiment", "emotion", "hate_speech"]:
        raise HTTPException(status_code=400, detail="Invalid category type")
    
    # Map category type to column name
    column_map = {
        "sentiment": "top_sentiment",
        "emotion": "top_emotion",
        "hate_speech": "top_hate_category"
    }
    column = column_map[category_type]
    
    # Query for posts
    posts = db.query(Post).join(
        PostSentiment
    ).filter(
        getattr(PostSentiment, column) == category
    ).order_by(
        Post.created_utc.desc()
    ).limit(limit).all()
    
    # Query for comments
    comments = db.query(Comment).join(
        CommentSentiment
    ).filter(
        getattr(CommentSentiment, column) == category
    ).order_by(
        Comment.created_utc.desc()
    ).limit(limit).all()
    
    return {
        "posts": [
            {
                "id": post.id,
                "title": post.title,
                "created_utc": post.created_utc
            }
            for post in posts
        ],
        "comments": [
            {
                "id": comment.id,
                "body": comment.body,
                "created_utc": comment.created_utc
            }
            for comment in comments
        ]
    }

@app.get("/trends")
def get_trends(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get sentiment/emotion trends over time"""
    # Calculate start timestamp (now - days)
    start_timestamp = int(time.time()) - (days * 86400)
    
    # Query for sentiment trends
    sentiment_query = """
    SELECT 
        date_trunc('day', to_timestamp(ps.created_utc)) AS day,
        ps.top_sentiment AS category,
        COUNT(*) AS count
    FROM 
        post_sentiments ps
    WHERE
        ps.created_utc >= :start_timestamp
    GROUP BY 
        day, ps.top_sentiment
    ORDER BY 
        day, ps.top_sentiment
    """
    
    # Query for emotion trends
    emotion_query = """
    SELECT 
        date_trunc('day', to_timestamp(ps.created_utc)) AS day,
        ps.top_emotion AS category,
        COUNT(*) AS count
    FROM 
        post_sentiments ps
    WHERE
        ps.created_utc >= :start_timestamp
    GROUP BY 
        day, ps.top_emotion
    ORDER BY 
        day, ps.top_emotion
    """
    
    # Execute queries
    sentiment_results = db.execute(sentiment_query, {"start_timestamp": start_timestamp}).fetchall()
    emotion_results = db.execute(emotion_query, {"start_timestamp": start_timestamp}).fetchall()
    
    # Format sentiment results
    sentiment_trends = {}
    for day, category, count in sentiment_results:
        day_str = day.isoformat()
        if day_str not in sentiment_trends:
            sentiment_trends[day_str] = {}
        sentiment_trends[day_str][category] = count
    
    # Format emotion results
    emotion_trends = {}
    for day, category, count in emotion_results:
        day_str = day.isoformat()
        if day_str not in emotion_trends:
            emotion_trends[day_str] = {}
        emotion_trends[day_str][category] = count
    
    return {
        "sentiment_trends": sentiment_trends,
        "emotion_trends": emotion_trends
    }

@app.post("/analyze/post/{post_id}")
def analyze_post(
    post_id: str,
    db: Session = Depends(get_db)
):
    """Manually trigger analysis for a specific post"""
    # Get post
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Analyze post title
    try:
        results = analyze_text(post.title)
        
        # Get highest scoring categories
        sentiment_category = max(
            results.get("sentiment", {}).items(), 
            key=lambda x: x[1] if x[1] is not None else 0,
            default=("unknown", 0)
        )[0]
        
        emotion_category = max(
            results.get("emotion", {}).items(), 
            key=lambda x: x[1] if x[1] is not None else 0,
            default=("unknown", 0)
        )[0]
        
        hate_category = max(
            results.get("hate_speech", {}).items(), 
            key=lambda x: x[1] if x[1] is not None else 0,
            default=("unknown", 0)
        )[0]
        
        # Create or update sentiment record
        current_time = int(time.time())
        post_sentiment = db.query(PostSentiment).filter(
            PostSentiment.post_id == post_id
        ).first()
        
        if post_sentiment:
            # Update existing record
            post_sentiment.clean_text = results["cleaned"]["clean"]
            post_sentiment.lemma_text = results["cleaned"]["lemma"]
            post_sentiment.char_count = results["cleaned"]["char_count"]
            post_sentiment.word_count = results["cleaned"]["word_count"]
            post_sentiment.sentiment_scores = results["sentiment"]
            post_sentiment.emotion_scores = results["emotion"]
            post_sentiment.hate_speech_scores = results["hate_speech"]
            post_sentiment.normalized_sentiment = results["normalized_sentiment"]
            post_sentiment.normalized_emotion = results["normalized_emotion"]
            post_sentiment.normalized_hate_speech = results["normalized_hate_speech"]
            post_sentiment.top_sentiment = sentiment_category
            post_sentiment.top_emotion = emotion_category
            post_sentiment.top_hate_category = hate_category
            post_sentiment.analyzed_utc = current_time
        else:
            # Create new record
            post_sentiment = PostSentiment(
                post_id=post_id,
                clean_text=results["cleaned"]["clean"],
                lemma_text=results["cleaned"]["lemma"],
                char_count=results["cleaned"]["char_count"],
                word_count=results["cleaned"]["word_count"],
                sentiment_scores=results["sentiment"],
                emotion_scores=results["emotion"],
                hate_speech_scores=results["hate_speech"],
                normalized_sentiment=results["normalized_sentiment"],
                normalized_emotion=results["normalized_emotion"],
                normalized_hate_speech=results["normalized_hate_speech"],
                top_sentiment=sentiment_category,
                top_emotion=emotion_category,
                top_hate_category=hate_category,
                created_utc=post.created_utc,
                analyzed_utc=current_time
            )
            db.add(post_sentiment)
        
        db.commit()
        
        return {
            "status": "success",
            "post_id": post_id,
            "sentiment": sentiment_category,
            "emotion": emotion_category
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")