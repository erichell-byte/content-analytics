# YouTube integration

This code has been added to the repository but **is not connected yet**.

## Security first
The OAuth client JSON was shared in a chat; rotate the OAuth client secret in Google Cloud before using it for production. Do not commit a client JSON, token JSON, or refresh token into the public GitHub repository. The project `.gitignore` excludes `youtube/token.json`; keep downloaded client files outside the repository.

## One-time local authorization
1. Ensure both YouTube Data API v3 and YouTube Analytics API are enabled and the signed-in Google account is on the OAuth test-user list.
2. Download the **rotated** OAuth Desktop client JSON from Google Cloud.
3. Install Python 3.10+ and dependencies: `python -m pip install -r youtube/requirements.txt`.
4. From the repository root run: `python youtube/connect.py --client-secrets /absolute/path/to/client.json`.
5. Sign in to the Google account that owns the YouTube channel and consent to read-only scopes. The script prints the selected channel name.
6. Store `youtube/token.json` privately. Never paste tokens into chats.

For a local snapshot:
```sh
YOUTUBE_CLIENT_FILE=/absolute/path/to/client.json YOUTUBE_TOKEN_FILE=youtube/token.json python youtube/collect.py
```

The snapshot goes into `data/youtube/YYYY-MM-DD.json`. It contains public video statistics and channel-level analytics; it does not currently fetch detailed per-video audience-retention curves.

**Google OAuth testing caveat:** refresh tokens for external apps in Testing mode generally expire after 7 days when YouTube scopes are requested. For a durable scheduled collector, address OAuth publishing/verification requirements and install protected CI secrets, then add a schedule. The repository remains public so committing collected analytics may disclose private metrics; prefer a private database or private storage instead.
