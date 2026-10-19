"""Collect authorized YouTube statistics to a dated JSON snapshot.

Environment:
  YOUTUBE_CLIENT_JSON: OAuth desktop client JSON string (GitHub Actions secret)
  YOUTUBE_TOKEN_JSON: Authorized refresh-token JSON string (GitHub Actions secret)

Optional local execution with paths:
  YOUTUBE_CLIENT_FILE=/path/to/client.json
  YOUTUBE_TOKEN_FILE=/path/to/token.json
"""
import json
import os
from datetime import date, timedelta, timezone, datetime
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]

def parse_config(name, fallback):
    value = os.environ.get(name)
    if value:
        return json.loads(value)
    path = os.environ.get(fallback)
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    raise RuntimeError(f"Provide {name} as a protected secret or set {fallback}.")

def main():
    client = parse_config("YOUTUBE_CLIENT_JSON", "YOUTUBE_CLIENT_FILE")
    token = parse_config("YOUTUBE_TOKEN_JSON", "YOUTUBE_TOKEN_FILE")
    config = client.get("installed") or client.get("web")
    if not config:
        raise RuntimeError("Invalid OAuth client configuration")
    credentials = Credentials.from_authorized_user_info(token, scopes=SCOPES)
    if not credentials.valid:
        if not credentials.refresh_token:
            raise RuntimeError("No refresh token. Reauthorize with offline access.")
        credentials.refresh(Request())
    youtube = build("youtube", "v3", credentials=credentials)
    analytics = build("youtubeAnalytics", "v2", credentials=credentials)
    channels = youtube.channels().list(part="snippet,contentDetails,statistics", mine=True).execute().get("items", [])
    if not channels:
        raise RuntimeError("No channel for these credentials")
    channel = channels[0]
    uploads_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    video_ids = []
    next_page = None
    while len(video_ids) < 200:
        data = youtube.playlistItems().list(part="contentDetails", playlistId=uploads_id,
                                            maxResults=50, pageToken=next_page).execute()
        video_ids.extend(item["contentDetails"]["videoId"] for item in data.get("items", []))
        next_page = data.get("nextPageToken")
        if not next_page:
            break
    videos = []
    for i in range(0, min(len(video_ids), 200), 50):
        data = youtube.videos().list(part="snippet,contentDetails,statistics",
                                      id=",".join(video_ids[i:i + 50]), maxResults=50).execute()
        for item in data.get("items", []):
            videos.append({"id": item["id"], "title": item["snippet"].get("title"),
                           "publishedAt": item["snippet"].get("publishedAt"),
                           "duration": item["contentDetails"].get("duration"),
                           "statistics": item.get("statistics", {})})
    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=27)
    try:
        report = analytics.reports().query(ids="channel==MINE",
            startDate=start.isoformat(), endDate=end.isoformat(),
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,subscribersGained",
            dimensions="day", sort="day").execute()
    except Exception as exc:
        raise RuntimeError("YouTube Analytics API request failed. Check access, scopes, and API activation.") from exc
    snapshot = {"collectedAt":datetime.now(timezone.utc).isoformat(),
                "channel":{"id":channel["id"],"title":channel["snippet"]["title"],
                           "statistics":channel.get("statistics", {})},
                "videos":videos,"dailyAnalytics":report}
    dest = Path("data/youtube") / f"{date.today().isoformat()}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Collected {len(videos)} videos; saved {dest}")

if __name__ == "__main__":
    main()
