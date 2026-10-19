import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common
import collect


class CollectorTests(unittest.TestCase):
    def test_private_atomic_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'private/token.json'
            common.write_json(path, {'example': 1})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(json.loads(path.read_text()), {'example': 1})
            self.assertEqual(list(path.parent.glob('.pending-*')), [])

    def test_repository_storage_rejected(self):
        with self.assertRaises(RuntimeError):
            common.private_dir(Path(common.__file__).resolve().parent / 'private')

    def test_lock_excludes_other_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            with common.locked(Path(tmp)):
                with self.assertRaises(RuntimeError):
                    with common.locked(Path(tmp)):
                        pass

    @patch('common.api')
    def test_wrong_channel_rejected(self, build):
        build.return_value.channels.return_value.list.return_value.execute.side_effect = [
            {'items': [{'id': 'expected'}]}, {'items': [{'id': 'other', 'snippet': {'title': 'Other'}}]}]
        with self.assertRaisesRegex(RuntimeError, 'Expected @tseyaketsa'):
            common.verified_channel(MagicMock())

    @patch('common.api')
    def test_matching_channel_verified(self, build):
        channel = {'id': 'expected'}
        build.return_value.channels.return_value.list.return_value.execute.side_effect = [
            {'items': [channel]}, {'items': [channel]}]
        self.assertEqual(common.verified_channel(MagicMock())[1], channel)

    @patch('common.Request')
    def test_refreshed_token_persisted(self, request):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            common.write_json(root / 'token.json', {'dummy': True})
            creds = MagicMock(valid=False, client_id='example', token_uri='https://oauth2.googleapis.com/token')
            creds.to_json.return_value = '{"refreshed":true}'
            with patch('common.Credentials.from_authorized_user_file', return_value=creds), patch('common.client_config', return_value={'installed': {'client_id': 'example', 'token_uri': creds.token_uri}}):
                common.credentials(root)
            creds.refresh.assert_called_once()
            self.assertTrue(json.loads((root / 'token.json').read_text())['refreshed'])

    @patch('collect.api')
    @patch('collect.verified_channel')
    @patch('collect.credentials')
    def test_upload_pagination_and_missing_days(self, creds, verified, build):
        youtube = MagicMock()
        verified.return_value = (youtube, {'id': 'expected', 'snippet': {'title': 'test'}, 'contentDetails': {'relatedPlaylists': {'uploads': 'uploads'}}})
        youtube.playlistItems.return_value.list.return_value.execute.side_effect = [
            {'items': [{'contentDetails': {'videoId': 'a'}}], 'nextPageToken': 'next'},
            {'items': [{'contentDetails': {'videoId': 'b'}}]}]
        youtube.videos.return_value.list.return_value.execute.return_value = {'items': []}
        build.return_value.reports.return_value.query.return_value.execute.return_value = {'columnHeaders': [{'name': 'day'}], 'rows': [['2026-01-02']]}
        with tempfile.TemporaryDirectory() as tmp:
            result = collect.collect(Path(tmp), date(2026, 1, 1), date(2026, 1, 3))
            self.assertEqual(result['coverage']['uploadIds'], 2)
            self.assertEqual(result['dailyAnalytics']['rows'], [['2026-01-02']])
            self.assertEqual(result['coverage']['lastReturnedDay'], '2026-01-02')
        query = build.return_value.reports.return_value.query.call_args.kwargs
        self.assertEqual(query['ids'], 'channel==expected')
        self.assertEqual(youtube.playlistItems.return_value.list.call_args.kwargs['pageToken'], 'next')


if __name__ == '__main__':
    unittest.main()
