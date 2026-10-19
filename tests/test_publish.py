import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

validate = module('validate-publish').validate
verify = module('verify-publish-files').verify

class PublishTests(unittest.TestCase):
    def test_run_provenance(self):
        valid = dict(repository={'full_name': 'edeori/Test'}, workflow_id=123,
                     status='completed', conclusion='success', event='workflow_dispatch', head_sha='a'*40)
        self.assertEqual(validate(valid, 'edeori/Test', 123), 'a'*40)
        for change in ({'conclusion':'failure'}, {'status':'in_progress'}, {'workflow_id':456},
                       {'repository':{'full_name':'other/Test'}}, {'event':'pull_request'}):
            with self.assertRaises(ValueError):
                validate({**valid, **change}, 'edeori/Test', 123)

    def test_scan_report_binds_installer(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'report').mkdir()
            (root/'installer.exe').write_bytes(b'installer'); (root/'installer.pkg').write_bytes(b'package')
            report={'result':'clean','scanExitCode':0,'installerSha256':hashlib.sha256(b'installer').hexdigest()}
            (root/'report/result.json').write_text(json.dumps(report))
            verify(root)
            (root/'installer.exe').write_bytes(b'changed')
            with self.assertRaises(ValueError): verify(root)
            (root/'installer.exe').write_bytes(b'installer')
            report['result']='failed'
            (root/'report/result.json').write_text(json.dumps(report))
            with self.assertRaises(ValueError): verify(root)
