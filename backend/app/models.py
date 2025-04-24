# backend/app/models.py
from sqlalchemy import Column, String, Integer, Float, ForeignKey
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

class Comment(Base):
    __tablename__ = "comments"
    id = Column(String, primary_key=True, index=True)
    post_id = Column(String, ForeignKey("posts.id"))
    body = Column(String)
    created_utc = Column(Integer)
    post = relationship("Post", back_populates="comments")

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String, ForeignKey("posts.id"))
    emotion = Column(String)
    score = Column(Float)
    created_utc = Column(Integer)
    post = relationship("Post", back_populates="predictions")
