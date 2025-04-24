# scripts/init_db.py
import os
from sqlalchemy import create_engine
from backend.app.models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://reddit_user:reddit_pass@localhost:5432/reddit_db"
)
engine = create_engine(DATABASE_URL)

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("✅ Tables created.")
