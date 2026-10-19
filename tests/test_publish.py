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

    def test_latest_ignores_failed_pr_and_other_branch_runs(self):
        select = module('validate-publish').select_latest
        def run(id, **extra):
            return dict(id=id, created_at=f'2026-10-{id:02d}', event='workflow_dispatch',
                        head_branch='main',status='completed',conclusion='success') | extra
        rows=[run(1),run(2),run(3,event='pull_request'),run(4,conclusion='failure'),run(5,head_branch='dev')]
        paths=[]
        def api(path):
            paths.append(path)
            return {'workflow_runs':rows}
        self.assertEqual(select(api,123,'main'),'2')
        self.assertIn('branch=main',paths[0])
        with self.assertRaises(ValueError): select(lambda _: {'workflow_runs':[]},123,'main')

    def test_latest_does_not_choose_old_build_rerun(self):
        select = module('validate-publish').select_latest
        rows=[dict(id=1,created_at='2026-10-01',updated_at='2026-10-19'),
              dict(id=2,created_at='2026-10-18',updated_at='2026-10-18')]
        rows=[r | dict(event='push',head_branch='main',status='completed',conclusion='success') for r in rows]
        self.assertEqual(select(lambda _: {'workflow_runs':rows},123,'main'),'2')
