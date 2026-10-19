import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from version_build import reserve, version_text, git

spec = importlib.util.spec_from_file_location('publish', Path(__file__).resolve().parents[1] / 'scripts/validate-publish.py')
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = self.root / 'remote.git'
        self.repo = self.root / 'repo'
        subprocess.run(['git', 'init', '--bare', str(self.remote)], check=True, capture_output=True)
        subprocess.run(['git', 'clone', str(self.remote), str(self.repo)], check=True, capture_output=True)
        git(self.repo, 'checkout', '-b', 'main')
        git(self.repo, 'config', 'user.name', 'test')
        git(self.repo, 'config', 'user.email', 'test@example.com')
        (self.repo / 'CMakeLists.txt').write_text('project(Test VERSION 0.1.9 LANGUAGES CXX)\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-m', 'initial')
        git(self.repo, 'push', 'origin', 'main')
        self.sha = git(self.repo, 'rev-parse', 'HEAD')

    def test_patch_and_rerun_are_one_atomic_reservation(self):
        m = reserve(self.repo, self.sha, 'refs/heads/main', '100', 'owner/repo')
        self.assertEqual(m['version'], '0.1.10')
        self.assertEqual(git(self.repo, 'ls-remote', 'origin', 'refs/heads/main').split()[0], m['source_sha'])
        git(self.repo, 'checkout', '--detach', self.sha)
        self.assertEqual(reserve(self.repo, self.sha, 'refs/heads/main', '100', 'owner/repo'), m)
        git(self.repo, 'checkout', '--detach', m['source_sha'])
        n = reserve(self.repo, m['source_sha'], 'refs/heads/main', '101', 'owner/repo')
        self.assertEqual(n['version'], '0.1.11')

    def test_stale_run_does_not_overwrite_developer_push(self):
        (self.repo / 'new.txt').write_text('new source')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-m', 'developer')
        latest = git(self.repo, 'rev-parse', 'HEAD')
        git(self.repo, 'push', 'origin', 'main')
        git(self.repo, 'checkout', '--detach', self.sha)
        with self.assertRaisesRegex(ValueError, 'Branch advanced'):
            reserve(self.repo, self.sha, 'refs/heads/main', '100', 'owner/repo')
        self.assertEqual(git(self.repo, 'ls-remote', 'origin', 'refs/heads/main').split()[0], latest)
        self.assertEqual(git(self.repo, 'ls-remote', 'origin', 'refs/tags/ci-build/100'), '')

    def test_tag_is_not_reversioned(self):
        m = reserve(self.repo, self.sha, 'refs/tags/v0.1.9', '100', 'owner/repo')
        self.assertEqual(m['source_sha'], self.sha)
        self.assertEqual(m['version'], '0.1.9')
        with self.assertRaisesRegex(ValueError, 'must match'):
            reserve(self.repo, self.sha, 'refs/tags/v9.0.0', '101', 'owner/repo')

    def test_multiline_and_invalid_versions(self):
        self.assertEqual(version_text('project(X\n VERSION 1.2.99\n LANGUAGES CXX)', True)[1], '1.2.100')
        for text in ['project(X VERSION 1.2)', 'project(X VERSION ${VERSION})', 'project(A VERSION 1.2.3)\nproject(B VERSION 1.2.3)']:
            with self.assertRaises(ValueError): version_text(text, True)

    def test_metadata_cannot_relabel_another_build(self):
        m = reserve(self.repo, self.sha, 'refs/heads/main', '100', 'owner/repo')
        self.assertEqual(publish.validate_metadata(m, 'owner/repo', '100', self.sha), (m['source_sha'], '0.1.10'))
        for key, value in [('repository', 'other/repo'), ('run_id', '101'), ('trigger_sha', 'a'*40), ('version', 'bad')]:
            with self.assertRaises(ValueError): publish.validate_metadata(dict(m, **{key:value}), 'owner/repo', '100', self.sha)
