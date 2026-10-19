"""Bind the downloaded Windows installer to its successful Defender report."""
import hashlib
import json
from pathlib import Path


def verify(root):
    root = Path(root)
    for name in ('installer.exe', 'installer.pkg'):
        if not (root / name).is_file() or (root / name).stat().st_size == 0:
            raise ValueError('Missing installer: ' + name)
    report = json.loads((root / 'report/result.json').read_text(encoding='utf-8-sig'))
    sha = hashlib.sha256((root / 'installer.exe').read_bytes()).hexdigest()
    if report.get('result') != 'clean' or report.get('scanExitCode') != 0:
        raise ValueError('A successful Defender report is required')
    if report.get('installerSha256', '').lower() != sha:
        raise ValueError('Installer does not match the Defender scan')
    print('Both installers exist; Windows installer matches its clean Defender report.')


if __name__ == '__main__':
    verify('dist')
