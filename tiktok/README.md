# Private TikTok collector for macOS

This integration uses Desktop Login Kit and the Display API with read-only
scopes: `user.info.basic`, `user.info.profile`, `user.info.stats`, `video.list`.
It cannot post, edit, or delete TikTok content.

## Portal setup

Use the existing Content Analytics application and its `Local Analytics`
Sandbox. Set platform Desktop, add Login Kit, and add the four scopes above.
Register this exact Desktop redirect URI:

`http://127.0.0.1:8765/callback/`

Save with Apply changes. Add the intended TikTok account under Target Users.
Sandbox account additions may take up to an hour to propagate. The app's
production approval and its Sandbox access are separate. A verified website
alone does not grant API access. Do not submit a production app without a real
end-to-end demo and accurate policies matching its actual data processing.

## Private credentials

Store a JSON file at:
`~/Library/Application Support/content-analytics/tiktok/client.json`
with `client_key`, `client_secret`, and `redirect_uri`. Copy the actual Sandbox
credentials privately from the portal; never place them in a checkout, chat,
GitHub secret, Actions artifact, or public website.

No credentials or private data are distributed in this repository.

## Run

Python 3.10+ (tested on 3.14). The existing project `.venv` can also be used.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tiktok/requirements.lock.txt
.venv/bin/python tiktok/connect.py --username EXPECTED_TIKTOK_USERNAME
.venv/bin/python tiktok/collect.py
```

Authorization opens TikTok in the system browser, starts a loopback callback,
validates state, and uses TikTok Desktop's specified SHA256 **hex** PKCE challenge.
The expected username and OAuth open_id must match the returned profile before
persisting authorization. Later runs pin the stable open_id, so a username change
does not silently switch the account. Tokens are bound to the saved client key.
The callback accepts only matching state on `/callback/` and waits ten minutes;
callback request URLs are never logged. `--no-browser` writes a temporary private
`authorization-url.json` for a browser controller; it is deleted when the flow ends.

The collector refreshes expiring access tokens without opening a browser and
atomically saves any rotated refresh token. API requests have timeouts, refuse
HTTP redirects, and retry transient failures for read-only endpoints. Token
exchanges are not blindly retried. User consent and valid platform access remain
required; the program does not bypass platform restrictions.

## Private data and meaning

All private state lives outside Git in the directory above. Directories have
0700 permissions, files 0600, writes are atomic, and a file lock prevents concurrent
operations. Raw error bodies, credentials and authorization URLs are not printed.
`status.json` records the latest result; `data/*.json` contains dated snapshots.
These are local files, not a database or separately encrypted vault. FileVault,
macOS account access and backup protection still matter.

Snapshots contain account counters and **lifetime** public-video counters:
views, likes, comments, shares, publication time and duration. Every list page
is fetched, duplicate IDs are removed, and a repeating pagination cursor fails
rather than writing a silently incomplete snapshot. Private/unavailable videos
are excluded by TikTok. These endpoints do not return historical daily views,
watch time or retention. Repeated snapshots provide a history from setup onward;
counter differences are net changes and can include platform corrections.
No metric absent from an API response is invented as zero.

## Daily automation

Only after a successful real collection:

```sh
.venv/bin/python tiktok/install_schedule.py
```

Installs a separate user LaunchAgent `local.content-analytics.tiktok` for 10:25
in the Mac system timezone, plus a run when loaded. Copies the runtime and
isolated dependencies into the private directory outside Documents. No need
to keep the checkout at a fixed location. Reinstall after code changes.
It requires the Mac/user session; no collection while powered off, and no
external failure notifications. Logs rotate at 256 KiB with three backups.

```sh
.venv/bin/python tiktok/install_schedule.py --remove
```

Removal retains private files. Token expiry/revocation or platform permission
changes may require interactive authorization again. Inspect private status/logs.

## Verification

```sh
.venv/bin/python -m unittest discover -s tiktok/tests -v
.venv/bin/python -m pip check
```

Mock tests cover callback state/code validation, scope checks, file permissions,
repository-storage rejection, wrong-account rejection, refresh-token rotation,
complete pagination/deduplication, cursor-loop rejection, and sanitized API errors.
Real authorization, data access, refresh and scheduled execution must be verified
separately for the intended account before reporting the connection as working.

Official references:
- https://developers.tiktok.com/docs/en/login-kit-desktop
- https://developers.tiktok.com/docs/en/oauth-user-access-token-management
- https://developers.tiktok.com/docs/en/tiktok-api-v2-get-user-info
- https://developers.tiktok.com/docs/en/tiktok-api-v2-video-list
- https://developers.tiktok.com/docs/en/add-a-sandbox
