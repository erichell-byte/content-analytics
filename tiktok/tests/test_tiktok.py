import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import client
import connect
import collect


class TikTokTests(unittest.TestCase):
    def test_callback_rejects_wrong_state_and_duplicate_code(self):
        for query in ({'state':['other'],'code':['one']}, {'state':['expected'],'code':['one','two']}):
            with self.assertRaises(client.TikTokError):
                connect.callback(query,'expected')
        self.assertEqual(connect.callback({'state':['expected'],'code':['one']},'expected'),'one')

    def test_token_requires_all_read_scopes(self):
        payload={'access_token':'fake-access','refresh_token':'fake-refresh','open_id':'id','expires_in':300,'refresh_expires_in':600,'scope':'user.info.basic'}
        with self.assertRaises(client.TikTokError):
            client.token_payload(payload,'key')
        payload['scope']=','.join(client.SCOPES)
        saved=client.token_payload(payload,'key')
        self.assertGreater(saved['expires_at'],time.time())

    def test_private_storage_permissions_and_git_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'private/token.json'
            client.write_json(path,{'fake':'test'})
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777,0o700)
        with self.assertRaises(client.TikTokError):
            client.private_dir(Path(client.__file__).resolve().parent/'private')

    def test_wrong_account_rejected(self):
        with self.assertRaises(client.TikTokError):
            client.validate_identity({'open_id':'other'},{'open_id':'expected'})

    @patch('client.request')
    @patch('client.config',return_value={'client_key':'key','client_secret':'fake'})
    def test_refresh_rotation_saved(self, config, request):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            client.write_json(root/'token.json',{'open_id':'id','client_key':'key','expires_at':0,'refresh_expires_at':time.time()+600,'refresh_token':'old-fake'})
            client.write_json(root/'account.json',{'open_id':'id'})
            request.return_value={'open_id':'id','access_token':'new-fake','refresh_token':'rotated-fake','expires_in':3600,'refresh_expires_in':60000,'scope':','.join(client.SCOPES)}
            token,_=client.credentials(root)
            self.assertEqual(token['refresh_token'],'rotated-fake')
            self.assertEqual(json.loads((root/'token.json').read_text())['refresh_token'],'rotated-fake')

    @patch('collect.request')
    def test_all_video_pages_and_deduplication(self, request):
        request.side_effect=[{'data':{'videos':[{'id':'a'}],'has_more':True,'cursor':100}}, {'data':{'videos':[{'id':'a'},{'id':'b'}],'has_more':False}}]
        self.assertEqual([v['id'] for v in collect.videos({'access_token':'fake'})],['a','b'])
        self.assertEqual(request.call_args.kwargs['body']['cursor'],100)

    @patch('collect.request')
    def test_repeated_cursor_fails_without_partial_result(self, request):
        request.return_value={'data':{'videos':[{'id':'a'}],'has_more':True,'cursor':0}}
        with self.assertRaises(client.TikTokError):
            collect.videos({'access_token':'fake'})

    @patch('client.requests.request')
    def test_error_body_secrets_not_in_error_and_redirects_disabled(self, request):
        request.return_value=MagicMock(status_code=400)
        request.return_value.json.return_value={'error':'invalid_grant','error_description':'sensitive-body'}
        with self.assertRaises(client.TikTokError) as error:
            client.request('/v2/oauth/token/',form={'client_secret':'fake'})
        self.assertNotIn('sensitive-body',str(error.exception))
        self.assertFalse(request.call_args.kwargs['allow_redirects'])
        self.assertEqual(request.call_count,1)


if __name__=='__main__':
    unittest.main()
