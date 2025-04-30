# frontend/app.py
import os
import time
import json
import requests
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime, timedelta
from sqlalchemy import create_engine

# Configuration
#API_URL = os.getenv("BACKEND_URL", "http://backend:5000")
API_URL = "http://backend:5000"  # Hardcode for testing
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://reddit_user:reddit_pass@postgres:5432/reddit_db"
)
engine = create_engine(DATABASE_URL)

# Page setup
st.set_page_config(
    page_title="Reddit Sentiment Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
try:
    debug_response = requests.get(f"{API_URL}/debug", timeout=5)
    if debug_response.status_code == 200:
        st.sidebar.success("Backend connection successful!")
    else:
        st.sidebar.error(f"Backend returned status code: {debug_response.status_code}")
except Exception as e:
    st.sidebar.error(f"Backend connection failed: {str(e)}")


# App title
st.title("📊 Reddit Sentiment Analyzer")
st.markdown("Analyze sentiment and emotions in Reddit posts and comments")

# Sidebar
st.sidebar.header("Controls")

# Subreddit input for data harvesting
with st.sidebar.expander("Harvest Data", expanded=False):
    harvest_subreddit = st.text_input("Subreddit", value="CryptoCurrency")
    harvest_limit = st.slider("Number of posts", min_value=10, max_value=500, value=100)
    
    if st.button("Harvest Data"):
        with st.spinner(f"Harvesting data from r/{harvest_subreddit}..."):
            try:
                response = requests.post(
                    f"{API_URL}/harvest/{harvest_subreddit}?limit={harvest_limit}",
                    timeout=60
                )
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"Successfully harvested {result['harvested']} posts from r/{harvest_subreddit}")
                    
                    # Add this line to clear the cache when new data is harvested
                    st.cache_data.clear()
                    
                else:
                    st.error(f"Failed to harvest data: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Date range filter
st.sidebar.header("Date Range")
days_options = {
    "Last 24 hours": 1,
    "Last 7 days": 7,
    "Last 30 days": 30,
    "Last 90 days": 90
}
selected_range = st.sidebar.selectbox("Select time range", list(days_options.keys()))
days = days_options[selected_range]

# Time period grouping for charts
group_by_options = {
    "Hourly": "hour",
    "Daily": "day",
    "Weekly": "week",
    "Monthly": "month"
}
selected_group = st.sidebar.selectbox(
    "Group data by",
    list(group_by_options.keys()),
    index=1 if days > 3 else 0
)
group_by = group_by_options[selected_group]

# Analysis type
analysis_types = ["Sentiment", "Emotion"]
selected_analysis = st.sidebar.radio("Analysis type", analysis_types)

# Test text analysis
st.sidebar.header("Text Analysis")
test_text = st.sidebar.text_area("Analyze custom text", height=100)
if st.sidebar.button("Analyze Text"):
    if test_text:
        with st.sidebar:
            with st.spinner("Analyzing..."):
                try:
                    response = requests.post(
                        f"{API_URL}/analyze/text",
                        params={"text": test_text},
                        timeout=30
                    )
                    if response.status_code == 200:
                        results = response.json()
                        
                        # Display sentiment
                        st.subheader("Sentiment")
                        sentiment_data = results.get("sentiment", {})
                        sentiment_df = pd.DataFrame({
                            "Score": sentiment_data.values(),
                            "Category": sentiment_data.keys()
                        })
                        st.bar_chart(sentiment_df.set_index("Category"))
                        
                        # Display emotion
                        st.subheader("Emotion")
                        emotion_data = results.get("emotion", {})
                        emotion_df = pd.DataFrame({
                            "Score": emotion_data.values(),
                            "Category": emotion_data.keys()
                        })
                        st.bar_chart(emotion_df.set_index("Category"))
                        
                    else:
                        st.error(f"Analysis failed: {response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    else:
        st.sidebar.warning("Please enter some text to analyze")

# Main content area
# Calculate timestamps
end_timestamp = int(time.time())
start_timestamp = end_timestamp - (days * 86400)

# Function to load trend data
@st.cache_data(ttl=600)
def load_trend_data(days):
    try:
        response = requests.get(f"{API_URL}/trends?days={days}", timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to load trends: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error loading trends: {str(e)}")
        return None

# Function to load stats data

@st.cache_data(ttl=600)
def load_stats_data(start_date, end_date, group_by, stats_type):
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            st.sidebar.info(f"Connecting to backend at {API_URL}/stats/{stats_type} (attempt {attempt+1})")
            response = requests.get(
                f"{API_URL}/stats/{stats_type}",
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "group_by": group_by
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            else:
                st.sidebar.error(f"Failed with status code: {response.status_code}, response: {response.text}")
                return None
        except Exception as e:
            st.sidebar.error(f"Error on attempt {attempt+1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                st.error(f"Error loading {stats_type} stats after {max_retries} attempts: {str(e)}")
                return None
            
# Function to prepare chart data
def prepare_chart_data(stats_data):
    if not stats_data:
        return pd.DataFrame()
    
    # Convert JSON to DataFrame
    rows = []
    for date_str, categories in stats_data.items():
        date = datetime.fromisoformat(date_str)
        for category, count in categories.items():
            rows.append({
                "date": date,
                "category": category,
                "count": count
            })
    
    return pd.DataFrame(rows)

def create_trend_chart(df, title):
    if df.empty:
        return None

    # Create pivot table for stacked chart
    pivot_df = df.pivot_table(
        index="date",
        columns="category",
        values="count",
        fill_value=0
    ).reset_index()

    # Melt the dataframe for Altair
    melted_df = pd.melt(
        pivot_df,
        id_vars=["date"],
        var_name="category",
        value_name="count"
    )

    color_scale = alt.Scale(
        domain=['positive', 'negative', 'neutral'],
        range=['#4CAF50', '#F44336', '#2196F3']
    )

    # Base chart
    chart = alt.Chart(melted_df).encode(
        x=alt.X("date:T", title="Date"),
        y=alt.Y("count:Q", title="Count"),
        color=alt.Color("category:N", scale=color_scale, legend=alt.Legend(title="Category")),
        tooltip=["date:T", "category:N", "count:Q"]
    ).properties(
        title=title,
        height=400
    )

    # Layered marks per category
    layers = []
    for category in pivot_df.columns[1:]:  # Skip 'date'
        layer = chart.transform_filter(
            alt.datum.category == category
        ).mark_area(
            opacity=0.2,
            line=True,
            strokeWidth=1
        )
        layers.append(layer)

    return alt.layer(*layers).resolve_scale(color='shared')


# Function to find examples for a category
@st.cache_data(ttl=10)
def get_examples(category_type, category, limit=5):
    try:
        response = requests.get(
            f"{API_URL}/examples/{category_type}/{category}",
            params={"limit": limit},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get examples: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error getting examples: {str(e)}")
        return None

# Main dashboard
# Load and display trend data based on selected analysis type
if selected_analysis == "Sentiment":
    stats_data = load_stats_data(start_timestamp, end_timestamp, group_by, "sentiment")
    df = prepare_chart_data(stats_data)
    chart = create_trend_chart(df, f"Sentiment Trends ({selected_range})")
    
    if chart:
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No sentiment data available for the selected time range")
    
    # Show examples for each sentiment category
    st.header("Example Posts by Sentiment")
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.write("Latest examples from analyzed posts")
    with col2:
        if st.button("↻", help="Refresh examples"):
            st.cache_data.clear()
            st.rerun()
    # Get unique categories
    if not df.empty:
        categories = df["category"].unique()
        cols = st.columns(min(3, len(categories)))
        
        for i, category in enumerate(categories[:3]):  # Limit to top 3 categories
            with cols[i]:
                st.subheader(f"{category.capitalize()}")
                examples = get_examples("sentiment", category, limit=3)
                
                if examples and examples.get("posts"):
                    for post in examples["posts"]:
                        st.markdown(f"**{post['title']}**")
                        st.markdown(f"*Posted: {datetime.fromtimestamp(post['created_utc'])}*")
                        st.markdown("---")
                else:
                    st.info(f"No examples found for {category}")

elif selected_analysis == "Emotion":
    stats_data = load_stats_data(start_timestamp, end_timestamp, group_by, "emotion")
    df = prepare_chart_data(stats_data)
    chart = create_trend_chart(df, f"Emotion Trends ({selected_range})")
    
    if chart:
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No emotion data available for the selected time range")
    
    # Show examples for each emotion category
    st.header("Example Posts by Emotion")
    # Get unique categories
    if not df.empty:
        categories = df["category"].unique()
        cols = st.columns(min(3, len(categories)))
        
        for i, category in enumerate(categories[:3]):  # Limit to top 3 categories
            with cols[i]:
                st.subheader(f"{category.capitalize()}")
                examples = get_examples("emotion", category, limit=3)
                
                if examples and examples.get("posts"):
                    for post in examples["posts"]:
                        st.markdown(f"**{post['title']}**")
                        st.markdown(f"*Posted: {datetime.fromtimestamp(post['created_utc'])}*")
                        st.markdown("---")
                else:
                    st.info(f"No examples found for {category}")

else:  # Hate Speech Analysis
    # Use SQL query for hate speech analysis (API endpoint not implemented for this)
    query = f"""
    SELECT 
        date_trunc('{group_by}', to_timestamp(ps.created_utc)) AS time_period,
        ps.top_hate_category AS category,
        COUNT(*) AS count
    FROM 
        post_sentiments ps
    WHERE
        ps.created_utc >= {start_timestamp}
        AND ps.created_utc <= {end_timestamp}
    GROUP BY 
        time_period, ps.top_hate_category
    ORDER BY 
        time_period, ps.top_hate_category
    """
    
    try:
        df = pd.read_sql(query, engine)
        if not df.empty:
            chart = create_trend_chart(df, f"Hate Speech Analysis ({selected_range})")
            if chart:
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No hate speech data available for the selected time range")
        else:
            st.info("No hate speech data available for the selected time range")
    except Exception as e:
        st.error(f"Error querying hate speech data: {str(e)}")

# Display summary statistics
st.header("Summary Statistics")

# SQL queries for statistics
if selected_analysis == "Sentiment":
    summary_query = f"""
    SELECT 
        ps.top_sentiment AS category,
        COUNT(*) AS count,
        COUNT(*) * 100.0 / (SELECT COUNT(*) FROM post_sentiments WHERE created_utc >= {start_timestamp} AND created_utc <= {end_timestamp}) AS percentage
    FROM 
        post_sentiments ps
    WHERE
        ps.created_utc >= {start_timestamp}
        AND ps.created_utc <= {end_timestamp}
    GROUP BY 
        ps.top_sentiment
    ORDER BY 
        count DESC
    """
elif selected_analysis == "Emotion":
    summary_query = f"""
    SELECT 
        ps.top_emotion AS category,
        COUNT(*) AS count,
        COUNT(*) * 100.0 / (SELECT COUNT(*) FROM post_sentiments WHERE created_utc >= {start_timestamp} AND created_utc <= {end_timestamp}) AS percentage
    FROM 
        post_sentiments ps
    WHERE
        ps.created_utc >= {start_timestamp}
        AND ps.created_utc <= {end_timestamp}
    GROUP BY 
        ps.top_emotion
    ORDER BY 
        count DESC
    """
else:  # Hate Speech
    summary_query = f"""
    SELECT 
        ps.top_hate_category AS category,
        COUNT(*) AS count,
        COUNT(*) * 100.0 / (SELECT COUNT(*) FROM post_sentiments WHERE created_utc >= {start_timestamp} AND created_utc <= {end_timestamp}) AS percentage
    FROM 
        post_sentiments ps
    WHERE
        ps.created_utc >= {start_timestamp}
        AND ps.created_utc <= {end_timestamp}
    GROUP BY 
        ps.top_hate_category
    ORDER BY 
        count DESC
    """

# Execute query and display results
try:
    summary_df = pd.read_sql(summary_query, engine)
    if not summary_df.empty:
        # Format percentage column
        summary_df["percentage"] = summary_df["percentage"].round(2)
        
        # Show as bar chart
        st.bar_chart(summary_df.set_index("category")["percentage"])
        
        # Show as table
        st.dataframe(summary_df.rename(columns={
            "category": "Category",
            "count": "Count",
            "percentage": "Percentage (%)"
        }))
    else:
        st.info(f"No {selected_analysis.lower()} data available for the selected time range")
except Exception as e:
    st.error(f"Error querying summary statistics: {str(e)}")

# Add information about sentiment shift
st.header("Biggest Sentiment Shifts")

# SQL query to find the biggest shift
shift_query = f"""
WITH daily_counts AS (
    SELECT 
        date_trunc('day', to_timestamp(ps.created_utc)) AS day,
        ps.top_sentiment AS sentiment,
        COUNT(*) AS count
    FROM 
        post_sentiments ps
    WHERE
        ps.created_utc >= {start_timestamp}
        AND ps.created_utc <= {end_timestamp}
    GROUP BY 
        day, ps.top_sentiment
),
daily_total AS (
    SELECT 
        day,
        SUM(count) AS total
    FROM 
        daily_counts
    GROUP BY 
        day
),
daily_percentages AS (
    SELECT 
        dc.day,
        dc.sentiment,
        dc.count,
        dc.count * 100.0 / dt.total AS percentage
    FROM 
        daily_counts dc
    JOIN 
        daily_total dt ON dc.day = dt.day
),
daily_changes AS (
    SELECT 
        day,
        sentiment,
        percentage,
        percentage - LAG(percentage) OVER (PARTITION BY sentiment ORDER BY day) AS change
    FROM 
        daily_percentages
)
SELECT 
    day,
    sentiment,
    change
FROM 
    daily_changes
WHERE 
    change IS NOT NULL
ORDER BY 
    ABS(change) DESC
LIMIT 5;
"""

try:
    shift_df = pd.read_sql(shift_query, engine)
    if not shift_df.empty:
        # Format the dataframe
        shift_df["day"] = pd.to_datetime(shift_df["day"])
        shift_df["change"] = shift_df["change"].round(2)
        
        # Show the data
        st.dataframe(shift_df.rename(columns={
            "day": "Date",
            "sentiment": "Sentiment",
            "change": "Change (%)"
        }))
        
        # Get posts from the day with the biggest shift
        biggest_shift_day = shift_df.iloc[0]["day"]
        posts_query = f"""
        SELECT 
            p.id,
            p.title,
            ps.top_sentiment,
            p.created_utc
        FROM 
            posts p
        JOIN 
            post_sentiments ps ON p.id = ps.post_id
        WHERE 
            date_trunc('day', to_timestamp(p.created_utc)) = '{biggest_shift_day.strftime('%Y-%m-%d')}'
            AND ps.top_sentiment = '{shift_df.iloc[0]["sentiment"]}'
        ORDER BY 
            p.created_utc
        LIMIT 3;
        """
        
        posts_df = pd.read_sql(posts_query, engine)
        if not posts_df.empty:
            st.subheader(f"Posts driving the shift on {biggest_shift_day.strftime('%Y-%m-%d')}")
            for _, post in posts_df.iterrows():
                st.markdown(f"**{post['title']}**")
                st.markdown(f"*Sentiment: {post['top_sentiment']}*")
                st.markdown(f"*Posted: {datetime.fromtimestamp(post['created_utc'])}*")
                st.markdown("---")
    else:
        st.info("No significant sentiment shifts detected in the selected time range")
except Exception as e:
    st.error(f"Error analyzing sentiment shifts: {str(e)}")