#!/usr/bin/env python3
# scripts/init_sentiment.py
"""
Initialize sentiment models and analyze existing data.
This script should be run after setting up the database and harvesting Reddit data.
"""
import os
import time
import logging
from datetime import datetime
try:
    from tqdm import tqdm
except ImportError:
    # Simple fallback if tqdm is not installed
    def tqdm(iterable, **kwargs):
        total = kwargs.get("total", len(iterable) if hasattr(iterable, "__len__") else None)
        desc = kwargs.get("desc", "")
        if total:
            print(f"{desc}: Processing {total} items...")
        return iterable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("init_sentiment")

# Setup database connection
import sys
sys.path.append("./backend")

try:
    from app.db import SessionLocal, engine
    from app.models import Base, Post, Comment, PostSentiment, CommentSentiment
    from app.sentiment_analyzer import analyze_text
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure you're running this script from the project root directory")
    sys.exit(1)

def initialize_database():
    """Create database tables if they don't exist"""
    logger.info("Initializing database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

def analyze_posts(batch_size=20):
    """Analyze post titles"""
    session = SessionLocal()
    
    try:
        # Get posts that haven't been analyzed yet
        total_posts = session.query(Post).outerjoin(
            PostSentiment
        ).filter(
            PostSentiment.id == None
        ).count()
        
        if total_posts == 0:
            logger.info("No posts found that need analysis")
            session.close()
            return
        
        logger.info(f"Found {total_posts} posts to analyze")
        
        # Process in batches to avoid memory issues
        offset = 0
        current_time = int(datetime.utcnow().timestamp())
        
        with tqdm(total=total_posts, desc="Analyzing posts") as pbar:
            while True:
                posts = session.query(Post).outerjoin(
                    PostSentiment
                ).filter(
                    PostSentiment.id == None
                ).order_by(Post.created_utc.desc()).limit(batch_size).offset(offset).all()
                
                if not posts:
                    break
                    
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
                        
                    except Exception as e:
                        logger.error(f"Error analyzing post {post.id}: {str(e)}")
                    
                    pbar.update(1)
                
                # Commit after each batch
                session.commit()
                
                # Move to next batch
                offset += batch_size
                
                # Small delay to prevent overloading
                time.sleep(0.1)
        
        session.close()
        logger.info("Post analysis complete")
    except Exception as e:
        logger.error(f"Error during post analysis: {str(e)}")
        session.close()

def analyze_comments(batch_size=20, max_comments=500):
    """Analyze comments"""
    session = SessionLocal()
    
    try:
        # Get comments that haven't been analyzed yet (limited to avoid very long processing)
        total_comments = session.query(Comment).outerjoin(
            CommentSentiment
        ).filter(
            CommentSentiment.id == None
        ).count()
        
        total_comments = min(total_comments, max_comments)
        
        if total_comments == 0:
            logger.info("No comments found that need analysis or max limit reached")
            session.close()
            return
        
        logger.info(f"Found {total_comments} comments to analyze (capped at {max_comments})")
        
        # Process in batches to avoid memory issues
        offset = 0
        current_time = int(datetime.utcnow().timestamp())
        
        with tqdm(total=total_comments, desc="Analyzing comments") as pbar:
            while offset < total_comments:
                comments = session.query(Comment).outerjoin(
                    CommentSentiment
                ).filter(
                    CommentSentiment.id == None
                ).order_by(Comment.created_utc.desc()).limit(batch_size).offset(offset).all()
                
                if not comments:
                    break
                    
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
                        
                    except Exception as e:
                        logger.error(f"Error analyzing comment {comment.id}: {str(e)}")
                    
                    pbar.update(1)
                
                # Commit after each batch
                session.commit()
                
                # Move to next batch
                offset += batch_size
                
                # Small delay to prevent overloading
                time.sleep(0.1)
        
        session.close()
        logger.info("Comment analysis complete")
    except Exception as e:
        logger.error(f"Error during comment analysis: {str(e)}")
        session.close()

def main():
    """Main function to run the initialization"""
    start_time = time.time()
    logger.info("Starting sentiment analysis initialization")
    
    try:
        # Create tables if needed
        initialize_database()
        
        # Analyze posts
        analyze_posts()
        
        # Analyze comments
        analyze_comments()
        
        elapsed_time = time.time() - start_time
        logger.info(f"Initialization complete in {elapsed_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Initialization failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()