"""Shared private storage and channel verification for the local collector."""
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

SCOPES = ['https://www.googleapis.com/auth/youtube.readonly',
          'https://www.googleapis.com/auth/yt-analytics.readonly']
PROJECT = 'content-analytics-512116'
HANDLE = '@tseyaketsa'
PRIVATE = Path.home() / 'Library/Application Support/content-analytics'


def private_dir(path):
    path = Path(path).expanduser().resolve()
    repo = Path(__file__).resolve().parents[1]
    if (repo / '.git').exists() and (path == repo or repo in path.parents):
        raise RuntimeError('Private storage must be outside the repository.')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def write_json(path, value):
    path = Path(path)
    parent = private_dir(path.parent)
    fd, temporary = tempfile.mkstemp(dir=parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def locked(root):
    path = private_dir(root) / 'collector.lock'
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, 'w') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another collector or authorization is already running.') from None
        yield


def client_config(path):
    config = json.loads(Path(path).expanduser().read_text())
    client = config.get('installed', {})
    if client.get('project_id') != PROJECT or not client.get('client_secret') or not client.get('client_id'):
        raise RuntimeError('Expected an OAuth Desktop client for ' + PROJECT)
    if client.get('auth_uri') != 'https://accounts.google.com/o/oauth2/auth' or client.get('token_uri') != 'https://oauth2.googleapis.com/token':
        raise RuntimeError('Unexpected OAuth endpoints.')
    return config


def credentials(root):
    token = root / 'token.json'
    if not token.exists():
        raise RuntimeError('Authorization required: run youtube/connect.py first.')
    token.chmod(0o600)
    creds = Credentials.from_authorized_user_file(str(token))
    config = client_config(root / 'client.json')['installed']
    if creds.client_id != config['client_id'] or creds.token_uri != config['token_uri']:
        raise RuntimeError('Token and Desktop client do not match; authorize again.')
    if not creds.has_scopes(SCOPES):
        raise RuntimeError('Read-only permissions are missing; authorize again.')
    if not creds.valid:
        if not creds.refresh_token:
            raise RuntimeError('No refresh token; authorize again.')
        creds.refresh(Request())
        write_json(token, json.loads(creds.to_json()))
    return creds


def api(name, version, creds):
    return build(name, version, http=AuthorizedHttp(creds, http=httplib2.Http(timeout=60)), cache_discovery=False)


def verified_channel(creds):
    youtube = api('youtube', 'v3', creds)
    target = youtube.channels().list(part='id,snippet', forHandle=HANDLE).execute(num_retries=3).get('items', [])
    owned = youtube.channels().list(part='snippet,contentDetails,statistics', mine=True).execute(num_retries=3).get('items', [])
    if len(target) != 1:
        raise RuntimeError('Cannot resolve expected handle ' + HANDLE)
    matching = [item for item in owned if item['id'] == target[0]['id']]
    if len(matching) != 1:
        raise RuntimeError('Selected channel(s): ' + ', '.join(c['snippet'].get('title', '') + ' (' + c['id'] + ')' for c in owned) + '. Expected ' + HANDLE + ' (' + target[0]['id'] + '); authorize the correct Google/Brand account.')
    return youtube, matching[0]
