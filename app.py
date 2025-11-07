# app.py
import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
from datetime import datetime

st.set_page_config(page_title="YouTube Analytics Dashboard", layout="wide")

st.title("YouTube Channel Analytics - VR Raja Facts")

# Connect to database
conn = sqlite3.connect("data.db")
df = pd.read_sql_query("SELECT * FROM videos", conn)
df['published_at'] = pd.to_datetime(df['published_at'])
conn.close()

# Sidebar filters
st.sidebar.header("Filters")
start_date = st.sidebar.date_input("Start date", df['published_at'].min())
end_date = st.sidebar.date_input("End date", df['published_at'].max())
keyword = st.sidebar.text_input("Keyword in title/description")

filtered_df = df[(df['published_at'].dt.date >= start_date) &
                 (df['published_at'].dt.date <= end_date)]

if keyword:
    filtered_df = filtered_df[
        filtered_df['title'].str.contains(keyword, case=False) |
        filtered_df['description'].str.contains(keyword, case=False)
    ]

st.subheader(f"Showing {len(filtered_df)} videos")

# Show table
st.dataframe(filtered_df[['published_at', 'title', 'view_count', 'like_count', 'comment_count', 'sentiment']].sort_values('published_at', ascending=False))

# Engagement summary
st.subheader("Engagement Summary")
total_views = filtered_df['view_count'].sum()
total_likes = filtered_df['like_count'].sum()
total_comments = filtered_df['comment_count'].sum()
avg_sentiment = filtered_df['sentiment'].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Views", f"{total_views:,}")
col2.metric("Total Likes", f"{total_likes:,}")
col3.metric("Total Comments", f"{total_comments:,}")
col4.metric("Average Sentiment", f"{avg_sentiment:.2f}")

# Sentiment over time
st.subheader("Sentiment Over Time")
sentiment_chart = alt.Chart(filtered_df).mark_line(point=True).encode(
    x='published_at:T',
    y='sentiment:Q',
    tooltip=['title', 'sentiment', 'view_count']
).interactive()

st.altair_chart(sentiment_chart, use_container_width=True)

# Top performing videos
st.subheader("Top 10 Videos by Views")
top_videos = filtered_df.sort_values('view_count', ascending=False).head(10)
st.table(top_videos[['title', 'view_count', 'like_count', 'comment_count', 'sentiment']])

from analysis import get_analysis
import streamlit as st

analysis = get_analysis()

st.title("Mental Well-Being Dashboard")

st.sidebar.subheader("Alerts")
st.sidebar.write("Weeks with high negative sentiment or low engagement:")
st.sidebar.write(analysis["alerts"])

import pandas as pd

top_hashtags = analysis["top_hashtags"]  # list of tuples
df_hashtags = pd.DataFrame(top_hashtags, columns=["Hashtag", "Count"])
st.sidebar.subheader("Top Hashtags")
st.sidebar.dataframe(df_hashtags)

st.sidebar.subheader("Best Posting Hour")

st.sidebar.subheader("Best Posting Time")

best_hour = analysis.get("best_hour")
best_day = analysis.get("best_day", "N/A")

# --- Convert numeric hour to readable AM/PM format ---
try:
    hour = int(best_hour)
    am_pm = "AM" if hour < 12 else "PM"
    hour_12 = hour % 12 if hour % 12 != 0 else 12
    formatted_hour = f"{hour_12}:00 {am_pm}"
except (ValueError, TypeError):
    formatted_hour = str(best_hour)

# --- Combine day + time nicely ---
if best_day != "N/A":
    st.sidebar.write(f"**{best_day} – {formatted_hour}**")
else:
    st.sidebar.write(formatted_hour)
 


# Example: show emotion distribution
st.subheader("Emotion Scores Example")
st.write(analysis["df"][['title','emotion_scores','toxicity_score']].head(10))
