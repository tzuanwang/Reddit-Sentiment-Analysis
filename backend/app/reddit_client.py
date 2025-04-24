# backend/app/reddit_client.py
import os
import praw
from .db import SessionLocal
from .models import Post, Comment

def get_reddit():
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )

def fetch_subreddit_data(subreddit_name: str, limit: int = 100):
    reddit = get_reddit()
    session = SessionLocal()
    fetched = []

    for submission in reddit.subreddit(subreddit_name).new(limit=limit):
        post = Post(
            id=submission.id,
            title=submission.title,
            created_utc=int(submission.created_utc)
        )
        session.merge(post)

        submission.comments.replace_more(limit=0)
        for c in submission.comments.list():
            comment = Comment(
                id=c.id,
                post_id=submission.id,
                body=c.body,
                created_utc=int(c.created_utc)
            )
            session.merge(comment)

        fetched.append(post)

    session.commit()
    session.close()
    return fetched
