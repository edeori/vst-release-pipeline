"""Configure a VST repository to call the public reusable release workflow."""
import argparse
import json
import re
import subprocess
import urllib.request
from pathlib import Path
from registry import NoRedirect, validate

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = 'edeori/vst-release-pipeline'
SECRET_NAMES = ['REGISTRY_TOKEN', 'APPLE_CERTIFICATES_P12', 'APPLE_CERTIFICATES_PASSWORD',
                'APPLE_ID', 'APPLE_APP_PASSWORD', 'APPLE_TEAM_ID', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY']


def gh(*args, value=None):
    return subprocess.check_output(['gh', *args], input=value, text=True, stderr=subprocess.PIPE)


def caller(product, revision):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', product):
        raise ValueError('Invalid product ID')
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Pipeline revision must be a full commit SHA')
    return '''name: Release installers
on:
  workflow_dispatch:
    inputs:
      publish:
        description: Replace live MinIO installers after both builds succeed
        type: boolean
        default: false
  push:
    tags: ['v*']
permissions:
  contents: read
jobs:
  release:
    uses: ''' + PIPELINE + '/.github/workflows/vst-release.yml@' + revision + '''
    with:
      product-id: ''' + product + '''
      publish: ${{ github.event_name == 'push' || inputs.publish }}
    secrets:
''' + ''.join('      ' + name + ': ${{ secrets.' + name + ' }}\n' for name in SECRET_NAMES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('product')
    parser.add_argument('repository')
    parser.add_argument('--checkout', required=True, type=Path)
    parser.add_argument('--server', default='mothstack')
    args = parser.parse_args()
    if not re.fullmatch(r'edeori/[A-Za-z0-9_.-]+', args.repository):
        raise ValueError('Expected an edeori source repository')
    revision = gh('api', f'repos/{PIPELINE}/commits/main', '--jq', '.sha').strip()
    contents = caller(args.product, revision)
    target = args.checkout.resolve() / '.github/workflows/release.yml'
    if target.exists() and target.read_text() != contents:
        raise ValueError('Caller workflow already exists; review and update it manually')
    remote = subprocess.check_output(['git', '-C', str(args.checkout), 'remote', 'get-url', 'origin'], text=True).strip()
    if remote.removesuffix('.git') not in [f'https://github.com/{args.repository}', f'git@github.com:{args.repository}']:
        raise ValueError('Checkout origin does not match the requested repository')
    for adapter in ('package-mac.sh', 'package-windows.ps1'):
        if not (args.checkout / 'ci' / adapter).is_file():
            raise ValueError('Missing local adapter: ci/' + adapter)
    shared = json.loads(subprocess.check_output(['swift', str(ROOT / 'scripts/keychain-secrets.swift'), 'read']))
    apple_names = [name for name in SECRET_NAMES if name.startswith('APPLE_')]
    if any(not shared.get(name) for name in apple_names):
        raise ValueError('Complete the local Apple credential setup first')
    env = subprocess.check_output(['ssh', args.server, 'cat /srv/mothproduction-web/.env'], text=True)
    token = next(line.split('=', 1)[1] for line in env.splitlines() if line.startswith('RELEASE_REGISTRY_TOKEN='))
    request = urllib.request.Request('https://mothproduction.hu/release-api/products/' + args.product,
                                     headers={'Authorization': 'Bearer ' + token})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
        validate(json.load(response), args.product, args.repository)
    storage = subprocess.check_output(['ssh', args.server, 'python3', '-', args.product],
                                      input=(ROOT / 'scripts/provision-storage.py').read_text(), text=True)
    credentials = json.loads(storage)
    values = {name: shared[name] for name in apple_names}
    values.update(REGISTRY_TOKEN=token, MINIO_ACCESS_KEY=credentials['access'], MINIO_SECRET_KEY=credentials['secret'])
    for name, value in values.items():
        gh('secret', 'set', name, '--repo', args.repository, value=value)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(contents)
    print(f'{args.repository}: caller workflow and repository secrets configured.')
    print('Review, commit and push the caller and adapters in the VST repository. Run Actions there.')


if __name__ == '__main__':
    main()
