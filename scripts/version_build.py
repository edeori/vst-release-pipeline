"""Reserve one patch version per branch build, atomically committing it upstream."""
import json
import os
from pathlib import Path
import re
import subprocess


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE).strip()


def version_text(text, bump=False):
    # Only the root project's literal three-part VERSION is supported.
    projects = list(re.finditer(r'(?im)^\s*project\s*\([^)]*\)', text))
    if len(projects) != 1:
        raise ValueError('Expected one root project() declaration')
    match = re.search(r'\bVERSION\s+([0-9]+)\.([0-9]+)\.([0-9]+)(?=\s|\))', projects[0].group(), re.I)
    if not match:
        raise ValueError('Root project VERSION must be a literal major.minor.patch')
    major, minor, patch = map(int, match.groups())
    version = f'{major}.{minor}.{patch + int(bump)}'
    a = projects[0].start() + match.start(1)
    b = projects[0].start() + match.end(3)
    return text[:a] + version + text[b:], version


def reserve(root, sha, ref, run_id, repository):
    root = Path(root)
    if not re.fullmatch(r'[0-9a-f]{40}', sha) or not re.fullmatch(r'[1-9][0-9]*', run_id):
        raise ValueError('Invalid source SHA or run ID')
    if git(root, 'status', '--porcelain'):
        raise ValueError('Version reservation requires a clean checkout')
    if git(root, 'rev-parse', 'HEAD') != sha:
        raise ValueError('Checkout differs from the triggering source')
    tag = f'refs/tags/ci-build/{run_id}'
    existing = git(root, 'ls-remote', 'origin', tag)
    if existing:
        git(root, 'fetch', 'origin', tag)
        git(root, 'checkout', '--detach', 'FETCH_HEAD')
        built = git(root, 'rev-parse', 'HEAD')
        if built != sha:
            if git(root, 'rev-parse', 'HEAD^') != sha:
                raise ValueError('Reserved build has a different source parent')
            if git(root, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD') != 'CMakeLists.txt':
                raise ValueError('Reservation changed files other than CMakeLists.txt')
            expected, _ = version_text(git(root, 'show', f'{sha}:CMakeLists.txt'), True)
            if (root / 'CMakeLists.txt').read_text().strip() != expected.strip():
                raise ValueError('Reserved version is not the expected patch increment')
        _, version = version_text((root / 'CMakeLists.txt').read_text())
    elif ref.startswith('refs/heads/'):
        git(root, 'check-ref-format', ref)
        remote = git(root, 'ls-remote', 'origin', ref).split()
        if not remote or remote[0] != sha:
            raise ValueError('Branch advanced after this run started; start a build from the current branch. No version was changed.')
        path = root / 'CMakeLists.txt'
        text, version = version_text(path.read_text(), True)
        path.write_text(text)
        git(root, 'config', 'user.name', 'github-actions[bot]')
        git(root, 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
        git(root, 'add', 'CMakeLists.txt')
        git(root, 'commit', '-m', f'chore: reserve version {version} for build {run_id} [skip ci]')
        built = git(root, 'rev-parse', 'HEAD')
        # No force: concurrent developer pushes cannot be overwritten. Atomic
        # update prevents reserving a tag without its corresponding branch commit.
        git(root, 'push', '--atomic', 'origin', f'HEAD:{ref}', f'HEAD:{tag}')
    elif ref.startswith('refs/tags/v'):
        _, version = version_text((root / 'CMakeLists.txt').read_text())
        if ref != f'refs/tags/v{version}':
            raise ValueError('Release tag must match project VERSION exactly')
        built = sha
        git(root, 'push', 'origin', f'HEAD:{tag}')
    else:
        raise ValueError('Only branch builds and matching vMAJOR.MINOR.PATCH tags are supported')
    return dict(schema=1, repository=repository, run_id=run_id, trigger_sha=sha,
                source_sha=built, source_ref=ref, version=version)


def main():
    metadata = reserve('source', os.environ['GITHUB_SHA'], os.environ['GITHUB_REF'],
                       os.environ['GITHUB_RUN_ID'], os.environ['GITHUB_REPOSITORY'])
    Path('release-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
        out.write(f"source_sha={metadata['source_sha']}\nversion={metadata['version']}\n")
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
        out.write(f"Version: **{metadata['version']}**\n\nBuild source: `{metadata['source_sha']}`\n\nTrigger: `{metadata['trigger_sha']}`\n")
    print(f"Reserved {metadata['version']} at {metadata['source_sha']}")


if __name__ == '__main__':
    main()
