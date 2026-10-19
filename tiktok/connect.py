"""Desktop OAuth with TikTok's SHA256-hex PKCE and a loopback callback."""
import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlsplit
import webbrowser
from client import ROOT, SCOPES, TikTokError, config, locked, normalized, private_dir, request, token_payload, user, write_json


def callback(query, state):
    if len(query.get('state', [])) != 1 or not hmac.compare_digest(query['state'][0], state):
        raise TikTokError('Invalid OAuth state.')
    if query.get('error'):
        raise TikTokError('TikTok authorization was denied.')
    codes = query.get('code', [])
    if len(codes) != 1 or not codes[0]:
        raise TikTokError('Missing authorization code.')
    return codes[0]


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', required=True, help='Expected TikTok username, verified before token persistence')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    root = private_dir(ROOT)
    client = config(root)
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path != '/callback/':
                self.send_error(404)
                return
            query = parse_qs(parsed.query, keep_blank_values=True)
            if len(query.get('state', [])) != 1 or not hmac.compare_digest(query['state'][0], state):
                self.send_error(400, 'Invalid state')
                return
            received.update(query)
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(b'Authorization received. You may close this tab.')

    with locked(root), HTTPServer(('127.0.0.1',8765), Handler) as server:
        server.timeout = 1
        url = 'https://www.tiktok.com/v2/auth/authorize/?' + urlencode({
            'client_key':client['client_key'], 'response_type':'code', 'scope':','.join(SCOPES),
            'redirect_uri':client['redirect_uri'], 'state':state,
            'code_challenge':hashlib.sha256(verifier.encode('ascii')).hexdigest(), 'code_challenge_method':'S256'})
        write_json(root / 'authorization-url.json', {'url':url})
        try:
            if not args.no_browser:
                webbrowser.open(url)
            print('Waiting for TikTok consent in the browser.', flush=True)
            deadline = time.monotonic() + 600
            while not received and time.monotonic() < deadline:
                server.handle_request()
            if not received:
                raise TikTokError('Authorization timed out; retry connect.py.')
            code = callback(received, state)
            token = token_payload(request('/v2/oauth/token/', form={
                'client_key':client['client_key'], 'client_secret':client['client_secret'],
                'grant_type':'authorization_code', 'code':code, 'redirect_uri':client['redirect_uri'],
                'code_verifier':verifier}), client['client_key'])
            profile = user(token)
            if normalized(profile.get('username','')) != normalized(args.username):
                raise TikTokError('Selected TikTok username differs from expected account; token was not saved.')
            write_json(root / 'account.json', {'open_id':profile['open_id'], 'username':profile['username'], 'display_name':profile.get('display_name')})
            write_json(root / 'token.json', token)
            print('Verified TikTok @' + profile['username'] + '. Authorization saved privately.')
        finally:
            (root / 'authorization-url.json').unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        main()
    except TikTokError as exc:
        print('Authorization stopped:', str(exc))
        raise SystemExit(1)
    except Exception as exc:
        print('Authorization stopped:', type(exc).__name__, '(private details omitted)')
        raise SystemExit(1)
