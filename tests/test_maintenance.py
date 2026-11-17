import copy
from pathlib import Path
import sys
import unittest
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from resolve_versions import fingerprint
from privacy_check import findings
from github_api import SafeRedirect
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'deeler'))
from version_check import reported_version


class MaintenanceTests(unittest.TestCase):
    def test_cli_banner_punctuation_is_not_part_of_version(self):
        self.assertEqual(reported_version('GitHub Copilot CLI 1.0.113.\n'), '1.0.113')
        self.assertEqual(reported_version('\x1b[32m0.73.1\x1b[0m\n'), '0.73.1')
        self.assertEqual(reported_version('0.73.10'), '0.73.10')
        self.assertIsNone(reported_version('no version'))

    def test_daily_timestamp_does_not_trigger_rebuild(self):
        old = {'resolved_at': 'yesterday', 'os_refresh': '2026-W47', 'agents': {'pi': '1'}}
        new = copy.deepcopy(old)
        new['resolved_at'] = 'today'
        self.assertEqual(fingerprint(old), fingerprint(new))
        new['agents']['pi'] = '2'
        self.assertNotEqual(fingerprint(old), fingerprint(new))

    def test_week_change_triggers_full_refresh(self):
        old = {'os_refresh': '2026-W47'}
        self.assertNotEqual(fingerprint(old), fingerprint({'os_refresh': '2026-W48'}))

    def test_private_deployment_values_are_rejected(self):
        # Synthetic values assembled here keep the checked-in fixture generic.
        self.assertIn('private network address', findings('10.' + '2.3.4'))
        self.assertIn('private machine name', findings('workstation.' + 'internal'))
        self.assertIn('personal filesystem path', findings('/' + 'Users/' + 'person/project/'))
        self.assertIn('non-example SSH hostname', findings('HostName ' + 'host.invalid'))
        self.assertEqual(findings('HostName agents.example.com\n127.0.0.1'), [])

    def test_artifact_redirect_does_not_leak_token(self):
        original = urllib.request.Request('https://api.github.com/artifact', headers={'Authorization': 'Bearer synthetic'})
        redirected = SafeRedirect().redirect_request(original, None, 302, '', {}, 'https://artifacts.example.com/file')
        self.assertFalse(redirected.has_header('Authorization'))
        same_host = SafeRedirect().redirect_request(original, None, 302, '', {}, 'https://api.github.com/next')
        self.assertTrue(same_host.has_header('Authorization'))


if __name__ == '__main__':
    unittest.main()
