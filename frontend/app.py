# frontend/app.py
import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

# connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://reddit_user:reddit_pass@postgres:5432/reddit_db"
)
engine = create_engine(DATABASE_URL)

st.title("Reddit Sentiment Shift")

subreddit = st.sidebar.text_input("Subreddit", value="example_subreddit")

@st.cache(ttl=600)
def load_data():
    sql = """
    SELECT
      date_trunc('day', to_timestamp(p.created_utc)) AS day,
      pr.emotion,
      COUNT(*) AS count
    FROM predictions pr
    JOIN posts p ON pr.post_id = p.id
    GROUP BY 1, pr.emotion
    ORDER BY 1;
    """
    return pd.read_sql(sql, engine)

df = load_data()
pivot = df.pivot(index="day", columns="emotion", values="count").fillna(0)

if pivot.empty: # catch the error of empty database
    st.warning("No data available yet! Please wait for data to be harvested.")
else:
    st.line_chart(pivot)

    # find the day with the biggest shift
    diff = pivot.diff().abs().sum(axis=1).idxmax()
    st.markdown(f"**Biggest shift on:** {diff.date()}")

    top = pd.read_sql(
        f"""
        SELECT p.title, pr.emotion, pr.score
        FROM predictions pr
        JOIN posts p ON pr.post_id = p.id
        WHERE date_trunc('day', to_timestamp(p.created_utc)) = '{diff.date()}'
        ORDER BY pr.score DESC
        LIMIT 1;
        """,
        engine
    )
    st.write("Post driving that shift:")
    st.write(top.iloc[0].title)
