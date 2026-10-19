"""Authorize the channel locally, then create a reusable private OAuth token.

Do not upload credentials.json or token.json to GitHub.
Run: python youtube/connect.py --client-secrets /path/to/downloaded_oauth_json
"""
import argparse
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-secrets", required=True)
    parser.add_argument("--output", default="youtube/token.json")
    args = parser.parse_args()
    flow = InstalledAppFlow.from_client_secrets_file(args.client_secrets, scopes=SCOPES)
    credentials = flow.run_local_server(host="localhost", port=0, open_browser=True, access_type="offline", prompt="consent")
    youtube = build("youtube", "v3", credentials=credentials)
    response = youtube.channels().list(part="snippet", mine=True).execute()
    channels = response.get("items", [])
    if not channels:
        raise RuntimeError("No accessible YouTube channel. Check the signed-in account or Brand Account.")
    print("Authorized YouTube channel:", channels[0]["snippet"]["title"])
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(credentials.to_json(), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    print("Token stored locally at", path, "— never commit or share it.")

if __name__ == "__main__":
    main()
