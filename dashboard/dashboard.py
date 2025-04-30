import streamlit as st
import pandas as pd
import requests

st.title("Reddit Sentiment Dashboard")

try:
    response = requests.get("http://localhost:8000/logs")
    df = pd.DataFrame(response.json())

    if not df.empty:
        sentiment = [c for c in df.columns if c.startswith("sentiment_")]
        emotion = [c for c in df.columns if c.startswith("emotion_")]
        hate = [c for c in df.columns if c.startswith("hate_")]

        st.subheader("Average Sentiment")
        st.bar_chart(df[sentiment].mean())

        st.subheader("Average Emotion")
        st.bar_chart(df[emotion].mean())

        st.subheader("Average Hate")
        st.bar_chart(df[hate].mean())

        st.subheader("Latest Logs")
        st.dataframe(df.tail(20))
    else:
        st.write("No data yet.")
except Exception as e:
    st.error(f"Failed to load logs: {e}")
