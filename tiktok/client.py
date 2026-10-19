"""TikTok read-only client. Credentials and raw API bodies are never logged."""
import fcntl
import json
import os
import re
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
import requests

ROOT = Path.home() / 'Library/Application Support/content-analytics/tiktok'
SCOPES = ('user.info.basic', 'user.info.profile', 'user.info.stats', 'video.list')
BASE = 'https://open.tiktokapis.com'
USER_FIELDS = 'open_id,display_name,username,follower_count,following_count,likes_count,video_count'
VIDEO_FIELDS = 'id,title,video_description,create_time,duration,share_url,view_count,like_count,comment_count,share_count'


class TikTokError(RuntimeError):
    pass


def private_dir(path):
    path = Path(path).expanduser().resolve()
    repo = Path(__file__).resolve().parents[1]
    if (repo / '.git').exists() and (path == repo or repo in path.parents):
        raise TikTokError('Private storage must be outside Git.')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def write_json(path, value):
    path = Path(path)
    parent = private_dir(path.parent)
    fd, name = tempfile.mkstemp(dir=parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def locked(root=ROOT):
    root = private_dir(root)
    fd = os.open(root / 'collector.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, 'w') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise TikTokError('Another TikTok operation is running.') from None
        yield


def read_json(path):
    path = Path(path)
    path.chmod(0o600)
    return json.loads(path.read_text())


def config(root=ROOT):
    result = read_json(root / 'client.json')
    if not result.get('client_key') or not result.get('client_secret'):
        raise TikTokError('Missing TikTok Desktop client credentials.')
    if result.get('redirect_uri') != 'http://127.0.0.1:8765/callback/':
        raise TikTokError('Expected configured loopback redirect URI.')
    return result


def safe_code(value):
    return value if isinstance(value, str) and re.fullmatch(r'[a-z_]{1,60}', value) else 'api_error'


def request(path, *, access_token=None, form=None, body=None, params=None):
    if path not in ('/v2/oauth/token/', '/v2/user/info/', '/v2/video/list/'):
        raise TikTokError('Unexpected API endpoint.')
    headers = {'Authorization': 'Bearer ' + access_token} if access_token else {}
    retries = 1 if form is not None else 4
    for attempt in range(retries):
        try:
            response = requests.request('POST' if form is not None or body is not None else 'GET',
                BASE + path, headers=headers, data=form, json=body, params=params,
                timeout=(15,60), allow_redirects=False)
        except requests.RequestException:
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
                continue
            raise TikTokError('network_error') from None
        if response.status_code in (429,500,502,503,504) and attempt + 1 < retries:
            time.sleep(2 ** attempt)
            continue
        try:
            data = response.json()
        except ValueError:
            raise TikTokError('non_json_response HTTP ' + str(response.status_code)) from None
        error = data.get('error', {})
        code = error.get('code', 'ok') if isinstance(error, dict) else error
        if not 200 <= response.status_code < 300 or code not in (None, '', 'ok'):
            raise TikTokError(safe_code(code) + ' HTTP ' + str(response.status_code))
        return data
    raise TikTokError('request_failed')


def normalized(name):
    return name.lstrip('@').casefold()


def user(token):
    result = request('/v2/user/info/', access_token=token['access_token'], params={'fields': USER_FIELDS})
    profile = result.get('data', {}).get('user', {})
    if not profile.get('open_id') or profile['open_id'] != token.get('open_id'):
        raise TikTokError('Token identity differs from API profile.')
    return profile


def validate_identity(profile, identity):
    if profile.get('open_id') != identity.get('open_id'):
        raise TikTokError('Authorized account does not match the pinned TikTok account.')
    # Stable open_id is authoritative after initial username verification.


def token_payload(response, client_key):
    if not all(response.get(k) for k in ('access_token','refresh_token','open_id','expires_in','refresh_expires_in')):
        raise TikTokError('Incomplete OAuth token response.')
    granted = set(response.get('scope','').split(','))
    if not set(SCOPES).issubset(granted):
        raise TikTokError('Required read-only scopes were not granted.')
    now = time.time()
    return {**response, 'expires_at': now + int(response['expires_in']),
            'refresh_expires_at': now + int(response['refresh_expires_in']), 'client_key': client_key}


def credentials(root=ROOT, force_refresh=False):
    client = config(root)
    token = read_json(root / 'token.json')
    identity = read_json(root / 'account.json')
    if token.get('client_key') != client['client_key'] or token.get('open_id') != identity.get('open_id'):
        raise TikTokError('Saved token, client or account do not match.')
    if time.time() >= token.get('refresh_expires_at', 0):
        raise TikTokError('Refresh token expired; authorize again.')
    if force_refresh or time.time() >= token.get('expires_at', 0) - 300:
        updated = token_payload(request('/v2/oauth/token/', form={
            'client_key': client['client_key'], 'client_secret': client['client_secret'],
            'grant_type': 'refresh_token', 'refresh_token': token['refresh_token']}), client['client_key'])
        if updated['open_id'] != identity['open_id']:
            raise TikTokError('Refreshed token belongs to another account.')
        write_json(root / 'token.json', updated)
        token = updated
    return token, identity
