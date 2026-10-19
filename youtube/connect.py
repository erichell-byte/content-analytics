"""Read-only Desktop OAuth with PKCE and a loopback callback."""
import argparse
import json
import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from common import PRIVATE, SCOPES, client_config, locked, private_dir, verified_channel, write_json


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-secrets', required=True)
    parser.add_argument('--private-dir', type=Path, default=PRIVATE)
    args = parser.parse_args()
    config = client_config(args.client_secrets)
    root = private_dir(args.private_dir)
    with locked(root):
        flow = InstalledAppFlow.from_client_config(config, scopes=SCOPES, autogenerate_code_verifier=True)
        creds = flow.run_local_server(host='127.0.0.1', port=0, open_browser=True,
            access_type='offline', prompt='consent select_account', timeout_seconds=600,
            authorization_prompt_message='Google sign-in opened in your system browser.',
            success_message='Authorization received. You may close this tab.')
        if not creds.refresh_token or not creds.has_scopes(SCOPES):
            raise RuntimeError('Offline access or required permissions missing; authorize again.')
        _, channel = verified_channel(creds)
        write_json(root / 'client.json', config)
        write_json(root / 'token.json', json.loads(creds.to_json()))
        write_json(root / 'channel.json', {'id': channel['id'], 'handle': '@tseyaketsa', 'title': channel['snippet']['title']})
        print('Verified @tseyaketsa:', channel['id'], channel['snippet']['title'])
        print('Authorization stored privately outside Git.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Authorization failed (' + type(exc).__name__ + '). No token was printed.')
        if isinstance(exc, RuntimeError):
            print(str(exc))
        raise SystemExit(1)
