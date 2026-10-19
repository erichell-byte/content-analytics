"""Collect lifetime counters from TikTok Display API into private snapshots."""
from datetime import datetime, timezone
import os
from client import ROOT, VIDEO_FIELDS, TikTokError, credentials, locked, request, user, validate_identity, write_json


def videos(token):
    result, ids, cursors = [], set(), set()
    cursor = 0
    while True:
        response = request('/v2/video/list/', access_token=token['access_token'],
            params={'fields': VIDEO_FIELDS}, body={'max_count':20, 'cursor':cursor})
        data = response.get('data', {})
        for video in data.get('videos', []):
            if video['id'] not in ids:
                result.append(video)
                ids.add(video['id'])
        if not data.get('has_more'):
            return result
        next_cursor = data.get('cursor')
        if next_cursor is None or next_cursor == cursor or next_cursor in cursors:
            raise TikTokError('TikTok pagination cursor did not progress; snapshot not saved.')
        cursors.add(cursor)
        cursor = next_cursor


def main():
    os.umask(0o077)
    with locked(ROOT):
        try:
            token, identity = credentials(ROOT)
            profile = user(token)
            validate_identity(profile, identity)
            entries = videos(token)
            now = datetime.now(timezone.utc)
            snapshot = {'schemaVersion':1, 'platform':'tiktok', 'collectedAt':now.isoformat(),
                'account':profile, 'videos':entries, 'coverage':{'videosReturned':len(entries),
                    'meaning':'Lifetime counters at collection time for available public videos, not historical daily analytics.',
                    'allPagesFetched':True}}
            dest = ROOT / 'data' / (now.strftime('%Y-%m-%dT%H%M%S.%fZ') + '.json')
            write_json(dest, snapshot)
            write_json(ROOT / 'status.json', {'ok':True, 'lastSuccess':now.isoformat(), 'snapshot':str(dest),
                'username':profile['username'], 'videos':len(entries)})
            print(f'Collected {len(entries)} public TikTok videos for @{profile["username"]}; saved privately.')
        except Exception as exc:
            write_json(ROOT / 'status.json', {'ok':False, 'failedAt':datetime.now(timezone.utc).isoformat(),
                'errorType':type(exc).__name__, 'error':str(exc) if isinstance(exc,TikTokError) else 'Private details omitted'})
            print('TikTok collection failed; see private status.json. No credentials logged.')
            raise SystemExit(1)


if __name__ == '__main__':
    main()
