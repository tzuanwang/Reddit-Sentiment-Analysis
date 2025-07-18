# backend/app/main.py
from fastapi import FastAPI, HTTPException
from .db import SessionLocal, engine
from .models import Base
from .reddit_client import fetch_subreddit_data

# create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/harvest/{subreddit}")
def harvest(subreddit: str):
    try:
        posts = fetch_subreddit_data(subreddit)
        return {"harvested": len(posts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
