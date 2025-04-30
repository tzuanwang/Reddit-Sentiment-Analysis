# backend/app/models.py
from sqlalchemy import Column, String, Integer, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Post(Base):
    __tablename__ = "posts"
    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    created_utc = Column(Integer)
    comments = relationship("Comment", back_populates="post")
    predictions = relationship("Prediction", back_populates="post")
    sentiment_analysis = relationship("PostSentiment", back_populates="post", uselist=False)

class Comment(Base):
    __tablename__ = "comments"
    id = Column(String, primary_key=True, index=True)
    post_id = Column(String, ForeignKey("posts.id"))
    body = Column(String)
    created_utc = Column(Integer)
    post = relationship("Post", back_populates="comments")
    sentiment_analysis = relationship("CommentSentiment", back_populates="comment", uselist=False)

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String, ForeignKey("posts.id"))
    emotion = Column(String)
    score = Column(Float)
    created_utc = Column(Integer)
    post = relationship("Post", back_populates="predictions")

# New models for advanced sentiment analysis
class PostSentiment(Base):
    __tablename__ = "post_sentiments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String, ForeignKey("posts.id"), unique=True)
    
    # Cleaned text data
    clean_text = Column(String)
    lemma_text = Column(String)
    char_count = Column(Integer)
    word_count = Column(Integer)
    
    # Raw scores (stored as JSON)
    sentiment_scores = Column(JSON)
    emotion_scores = Column(JSON)
    hate_speech_scores = Column(JSON)
    
    # Normalized scores (stored as JSON)
    normalized_sentiment = Column(JSON)
    normalized_emotion = Column(JSON)
    normalized_hate_speech = Column(JSON)
    
    # Highest scoring categories
    top_sentiment = Column(String)
    top_emotion = Column(String)
    top_hate_category = Column(String)
    
    # Timestamps
    created_utc = Column(Integer)
    analyzed_utc = Column(Integer)
    
    # Relationships
    post = relationship("Post", back_populates="sentiment_analysis")

class CommentSentiment(Base):
    __tablename__ = "comment_sentiments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    comment_id = Column(String, ForeignKey("comments.id"), unique=True)
    
    # Cleaned text data
    clean_text = Column(String)
    lemma_text = Column(String)
    char_count = Column(Integer)
    word_count = Column(Integer)
    
    # Raw scores (stored as JSON)
    sentiment_scores = Column(JSON)
    emotion_scores = Column(JSON)
    hate_speech_scores = Column(JSON)
    
    # Normalized scores (stored as JSON)
    normalized_sentiment = Column(JSON)
    normalized_emotion = Column(JSON)
    normalized_hate_speech = Column(JSON)
    
    # Highest scoring categories
    top_sentiment = Column(String)
    top_emotion = Column(String)
    top_hate_category = Column(String)
    
    # Timestamps
    created_utc = Column(Integer)
    analyzed_utc = Column(Integer)
    
    # Relationships
    comment = relationship("Comment", back_populates="sentiment_analysis")