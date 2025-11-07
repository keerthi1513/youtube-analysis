# fetch_youtube.py

import os
from dotenv import load_dotenv
import sqlite3
from googleapiclient.discovery import build
from textblob import TextBlob
from datetime import datetime

# Load .env
load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_HANDLE = os.getenv("YOUTUBE_CHANNEL_ID")  # e.g., @Vrrajafacts

if not API_KEY:
    raise ValueError("Set YOUTUBE_API_KEY in your .env file")
if not CHANNEL_HANDLE:
    raise ValueError("Set YOUTUBE_CHANNEL_ID in your .env file")

print("API_KEY loaded:", API_KEY)
print("Channel handle:", CHANNEL_HANDLE)


# Helper: resolve handle to channel ID
def get_channel_id(api_key, handle):
    youtube = build("youtube", "v3", developerKey=api_key)
    res = youtube.search().list(q=handle, type="channel", part="snippet", maxResults=1).execute()
    items = res.get("items", [])
    if not items:
        raise ValueError(f"Cannot find channel with handle {handle}")
    return items[0]["snippet"]["channelId"]


# Database setup
def create_db(conn):
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        video_id TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        published_at TEXT,
        view_count INTEGER,
        like_count INTEGER,
        comment_count INTEGER,
        sentiment REAL,
        fetched_at TEXT
    )
    ''')
    conn.commit()


# Sentiment calculation
def sentiment_score(text):
    if not text:
        return 0.0
    return TextBlob(text).sentiment.polarity  # -1..1


# Fetch videos from channel
def fetch_videos(api_key, channel_id):
    youtube = build('youtube', 'v3', developerKey=api_key)

    # Get uploads playlist
    ch = youtube.channels().list(part='contentDetails', id=channel_id).execute()
    uploads_playlist_id = ch['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    videos = []
    next_page = None

    while True:
        pl = youtube.playlistItems().list(
            part='snippet',
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page
        ).execute()

        for item in pl['items']:
            snip = item['snippet']
            videos.append({
                'video_id': snip['resourceId']['videoId'],
                'title': snip.get('title'),
                'description': snip.get('description'),
                'published_at': snip.get('publishedAt')
            })

        next_page = pl.get('nextPageToken')
        if not next_page:
            break

    # Fetch stats in chunks of 50
    results = []
    for i in range(0, len(videos), 50):
        chunk = videos[i:i + 50]
        ids = ",".join([v['video_id'] for v in chunk])
        stats = youtube.videos().list(part='statistics', id=ids).execute()
        stats_map = {it['id']: it.get('statistics', {}) for it in stats['items']}
        for v in chunk:
            s = stats_map.get(v['video_id'], {})
            results.append({
                **v,
                'view_count': int(s.get('viewCount', 0)),
                'like_count': int(s.get('likeCount', 0)),
                'comment_count': int(s.get('commentCount', 0))
            })

    return results


# Main
def main():
    channel_id = get_channel_id(API_KEY, CHANNEL_HANDLE)
    print("Resolved channel ID:", channel_id)

    conn = sqlite3.connect('data.db')
    create_db(conn)

    videos = fetch_videos(API_KEY, channel_id)
    cur = conn.cursor()

    for v in videos:
        s = sentiment_score((v['title'] or "") + " " + (v['description'] or ""))
        cur.execute('''
        INSERT OR REPLACE INTO videos (video_id, title, description, published_at, view_count, like_count, comment_count, sentiment, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            v['video_id'], v['title'], v['description'], v['published_at'],
            v['view_count'], v['like_count'], v['comment_count'], s, datetime.utcnow().isoformat()
        ))

    conn.commit()
    conn.close()
    print(f"Inserted {len(videos)} videos.")


if __name__ == "__main__":
    main()
