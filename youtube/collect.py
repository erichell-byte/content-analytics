"""Collect verified channel statistics into private, atomic snapshots."""
import argparse
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from common import PRIVATE, api, credentials, locked, private_dir, verified_channel, write_json


def collect(root, start=None, end=None):
    creds = credentials(root)
    youtube, channel = verified_channel(creds)
    analytics = api('youtubeAnalytics', 'v2', creds)
    # YouTube Analytics days use Pacific time. Leave two days for processing.
    end = end or (datetime.now(ZoneInfo('America/Los_Angeles')).date() - timedelta(days=2))
    start = start or end - timedelta(days=27)
    if start > end or end >= datetime.now(ZoneInfo('America/Los_Angeles')).date():
        raise RuntimeError('Invalid report dates; use completed Pacific calendar days.')
    ids, page = [], None
    while True:
        data = youtube.playlistItems().list(part='contentDetails',
            playlistId=channel['contentDetails']['relatedPlaylists']['uploads'],
            maxResults=50, pageToken=page).execute(num_retries=3)
        ids.extend(item['contentDetails']['videoId'] for item in data.get('items', []))
        page = data.get('nextPageToken')
        if not page:
            break
    ids = list(dict.fromkeys(ids))
    videos = []
    for i in range(0, len(ids), 50):
        data = youtube.videos().list(part='snippet,contentDetails,statistics',
            id=','.join(ids[i:i+50])).execute(num_retries=3)
        for item in data.get('items', []):
            videos.append({'id': item['id'], 'title': item['snippet']['title'],
                'publishedAt': item['snippet']['publishedAt'],
                'duration': item['contentDetails']['duration'], 'statistics': item.get('statistics', {})})
    rows, offset, headers = [], 1, None
    while True:
        report = analytics.reports().query(ids='channel==' + channel['id'],
            startDate=start.isoformat(), endDate=end.isoformat(),
            metrics='views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,subscribersGained,subscribersLost',
            dimensions='day', sort='day', maxResults=200, startIndex=offset).execute(num_retries=3)
        headers = report.get('columnHeaders', headers)
        batch = report.get('rows', [])
        rows.extend(batch)
        if len(batch) < 200:
            break
        offset += len(batch)
    now = datetime.now(timezone.utc)
    snapshot = {'schemaVersion': 1, 'collectedAt': now.isoformat(),
        'requestedPeriod': {'start': start.isoformat(), 'end': end.isoformat(), 'timezone': 'America/Los_Angeles'},
        'coverage': {'uploadIds': len(ids), 'videosReturned': len(videos),
            'dailyRows': len(rows), 'lastReturnedDay': rows[-1][0] if rows else None,
            'note': 'Missing days are not assumed to be zero. Video statistics are lifetime counters at collection time, not period metrics.'},
        'channel': {'id': channel['id'], 'handle': '@tseyaketsa', 'title': channel['snippet']['title'], 'statistics': channel.get('statistics', {})},
        'videos': videos, 'dailyAnalytics': {'columnHeaders': headers, 'rows': rows}}
    dest = root / 'data/youtube' / (now.strftime('%Y-%m-%dT%H%M%S.%fZ') + '.json')
    write_json(dest, snapshot)
    write_json(root / 'status.json', {'ok': True, 'lastSuccess': now.isoformat(), 'snapshot': str(dest), 'channelId': channel['id'], 'dailyRows': len(rows), 'videos': len(videos)})
    print(f'Collected {len(videos)} videos, {len(rows)} daily rows; channel {channel["id"]}.')
    print('Private snapshot:', dest)
    return snapshot


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-dir', type=Path, default=PRIVATE)
    parser.add_argument('--start', type=date.fromisoformat)
    parser.add_argument('--end', type=date.fromisoformat)
    args = parser.parse_args()
    root = private_dir(args.private_dir)
    with locked(root):
        try:
            collect(root, args.start, args.end)
        except Exception as exc:
            # Exception bodies/URLs may contain sensitive request information.
            write_json(root / 'status.json', {'ok': False, 'failedAt': datetime.now(timezone.utc).isoformat(),
                'errorType': type(exc).__name__, 'httpStatus': getattr(getattr(exc, 'resp', None), 'status', None),
                'action': 'Check connectivity, API access and OAuth authorization. Re-run connect.py if access expired.'})
            print('Collection failed (' + type(exc).__name__ + '); see private status.json. No credentials were logged.')
            raise SystemExit(1)


if __name__ == '__main__':
    main()
