# Private YouTube collector on macOS

Collects read-only statistics for **@tseyaketsa** using the Google Cloud project
`content-analytics-512116`. No credentials or private reports belong in GitHub,
GitHub Pages, Actions artifacts, or chat messages.

## Setup

Python 3.10+ is required (tested locally on Python 3.14).

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r youtube/requirements.lock.txt
.venv/bin/python youtube/connect.py --client-secrets /absolute/path/to/rotated-desktop-client.json
.venv/bin/python youtube/collect.py
```

Use the current rotated Desktop client downloaded from Google Cloud. The program
checks the project and Google OAuth endpoints, uses PKCE with a random local
loopback port, and opens the system browser. Select the Google/Brand account
owning @tseyaketsa and grant `youtube.readonly` and `yt-analytics.readonly`.
The handle is resolved through YouTube Data API and its channel ID must match
an authorized channel before any token is persisted or report is saved.
This check runs for every collection, not only at authorization.

If Google rejects access, verify the account is an OAuth test user, both APIs
are enabled, the client is a Desktop client, and the chosen Brand Account owns
the target channel. Authorization times out after ten minutes; rerun to retry.
No secrets are printed in error output.

## Private storage

Default: `~/Library/Application Support/content-analytics/` outside the repository.

- `client.json`, `token.json`: OAuth configuration and reusable authorization.
- `channel.json`: verified channel identity.
- `data/youtube/*.json`: timestamped snapshots; existing snapshots are retained.
- `status.json`: result of the latest attempt, suitable for local inspection.
- `logs/collector.log`: scheduled run log, rotated at 256 KiB, three backups.

Directories are owner-only (0700), JSON files are atomically replaced with
owner-only permissions (0600), and a process lock prevents concurrent writers.
Refreshed tokens are saved. Collection never starts an interactive login.
Local permissions protect against other OS users, not software running as your
user or administrators. These files are not separately encrypted; use macOS
FileVault and account security. Device backups may include this directory.
The original client download is not deleted or altered by setup.

`--private-dir /absolute/private/path` works for manual connection/collection.
The scheduler intentionally uses the default directory.

## Data meaning

By default, the collector requests 28 inclusive days ending two Pacific-calendar
days before the current Pacific date. YouTube may return fewer days because of
processing latency; absent rows are not filled with zeros. The snapshot records
requested dates, returned rows, and the last returned day. Historical ranges:

```sh
.venv/bin/python youtube/collect.py --start 2026-09-01 --end 2026-09-30
```

Daily channel metrics: views, watch minutes, average view duration, average view
percentage, likes, comments, subscribers gained and lost. All upload-playlist
pages and video batches are fetched without the old 200-video cap. Video counters
are lifetime totals at collection time, not metrics for the requested period;
private, removed or otherwise unavailable videos may be absent. Subscriber
counts may be rounded by YouTube. No revenue, per-video retention curve,
TikTok, Instagram or Threads data is collected. Channel timezone for reports is
America/Los_Angeles; collection timestamps use UTC.

## Daily local automation

After a successful real collection:

```sh
.venv/bin/python youtube/install_schedule.py
```

Installs `~/Library/LaunchAgents/local.content-analytics.youtube.plist` for 10:15
in the Mac's system timezone, plus an immediate run when the agent is loaded.
It runs in your logged-in user session. macOS can catch up after sleep; it does
not collect while powered off and has no cloud availability guarantee.
A later login loads the agent again. The installer copies the collector and creates an isolated runtime under the
private storage directory, so moving the working repository does not break it.
Re-run the installer after code updates to refresh that runtime.
Network/server failures use API retries; a failed run updates private status.
There is no external failure notification. Inspect status/logs after failures.

```sh
.venv/bin/python youtube/install_schedule.py --remove
```

Google external OAuth apps in **Testing** normally have seven-day refresh tokens
for these scopes. Confirm publishing status in Google Cloud; changing it and any
verification requirements are separate from local setup. Tokens can also be
revoked, so unattended access is never guaranteed. Re-run connect.py when needed.
Do not upload refresh tokens to GitHub to work around this limitation.

## Verification

```sh
.venv/bin/python -m unittest discover -s youtube/tests -v
.venv/bin/python -m pip check
```

Tests cover file permissions, refusal of repository storage, process locking,
wrong-channel rejection, matching-channel acceptance, refreshed-token saving,
and upload pagination without fabricating missing report days. Real API and
refresh checks must additionally be performed after interactive consent.

Google references:
- https://developers.google.com/youtube/reporting/guides/authorization/installed-apps
- https://developers.google.com/youtube/analytics/reference/reports/query
- https://developers.google.com/identity/protocols/oauth2
