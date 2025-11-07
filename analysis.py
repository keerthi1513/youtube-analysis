# analysis.py
import pandas as pd
import sqlite3
import re
from collections import Counter
from transformers import pipeline

# -------------------------------
# Connect to SQLite database
# -------------------------------
conn = sqlite3.connect("data.db")
df = pd.read_sql_query("SELECT * FROM videos", conn)
df['published_at'] = pd.to_datetime(df['published_at'])
conn.close()

# -------------------------------
# Engagement Analytics
# -------------------------------
df = df.sort_values('published_at')
df['view_growth'] = df['view_count'].diff()
df['like_growth'] = df['like_count'].diff()
df['comment_growth'] = df['comment_count'].diff()
df['engagement_rate'] = (df['like_count'] + df['comment_count']) / df['view_count']
df['hour'] = df['published_at'].dt.hour
best_hour = df.groupby('hour')['view_count'].mean().idxmax()

# Top Hashtags
hashtags = []
for desc in df['description'].fillna(''):
    hashtags.extend(re.findall(r"#(\w+)", desc))
top_hashtags = Counter(hashtags).most_common(10)

# -------------------------------
# Emotion & Sentiment Analysis
# -------------------------------
# Hugging Face emotion model
emotion_analyzer = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    return_all_scores=True
)

MAX_CHARS = 2000  # safe truncation limit

def analyze_emotion(text):
    if not text:
        return []
    truncated = text[:MAX_CHARS]
    try:
        return emotion_analyzer(truncated)
    except:
        return []

# Combine title + description
df['text_for_analysis'] = df['title'].fillna('') + " " + df['description'].fillna('')
df['emotion_scores'] = df['text_for_analysis'].apply(analyze_emotion)

# Fix nested list issue
def is_negative(scores):
    if not scores or len(scores)==0:
        return False
    if isinstance(scores[0], list):  # flatten nested list
        scores = scores[0]
    for s in scores:
        if s['label'].lower() in ['sadness', 'anger', 'fear'] and s['score'] > 0.5:
            return True
    return False

df['negative_sentiment'] = df['emotion_scores'].apply(is_negative)

# -------------------------------
# Toxicity / Cyberbullying Detection
# -------------------------------
toxicity_model = pipeline(
    "text-classification",
    model="unitary/toxic-bert",
    return_all_scores=True
)

def analyze_toxicity(text):
    if not text:
        return 0
    truncated = text[:512]  # safe limit
    try:
        return toxicity_model(truncated)[0]['score']
    except:
        return 0

df['toxicity_score'] = df['description'].apply(analyze_toxicity)

# -------------------------------
# Behavioral Change / Stress Detection
# -------------------------------
weekly_activity = df.set_index('published_at').resample('W').size()
weekly_negative = df.set_index('published_at').resample('W')['negative_sentiment'].sum()

# Flag weeks with >50% negative content
alert_weeks = weekly_negative[weekly_negative > (weekly_activity/2)]

# -------------------------------
# Function to return analysis results
# -------------------------------
def get_analysis():
    return {
        "best_hour": best_hour,
        "top_hashtags": top_hashtags,
        "alerts": alert_weeks,
        "df": df
    }
