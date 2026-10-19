"""Provision one product's central environment without granting source write access."""
import argparse
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from registry import validate
from resolve import resolve

ROOT = Path(__file__).resolve().parents[1]
CENTRAL = 'edeori/vst-release-pipeline'


def gh(*args, value=None):
    return subprocess.check_output(['gh', *args], input=value, text=True, stderr=subprocess.PIPE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('product')
    parser.add_argument('repository')
    parser.add_argument('--server', default='mothstack')
    args = parser.parse_args()
    resolve(args.product, {args.product: {'repository': args.repository}})
    products_path = ROOT / 'products.json'
    products = json.loads(products_path.read_text())
    if args.product in products and products[args.product]['repository'] != args.repository:
        raise ValueError('Product is already assigned to another repository')
    # Validate the live Shop record and adapter contract before changing credentials.
    for adapter in ('package-mac.sh', 'package-windows.ps1'):
        gh('api', f'repos/{args.repository}/contents/ci/{adapter}')
    env = subprocess.check_output(['ssh', args.server, 'cat /srv/mothproduction-web/.env'], text=True)
    token = next(line.split('=', 1)[1] for line in env.splitlines() if line.startswith('RELEASE_REGISTRY_TOKEN='))
    from registry import NoRedirect
    request = urllib.request.Request('https://mothproduction.hu/release-api/products/' + args.product,
                                     headers={'Authorization': 'Bearer ' + token})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
        validate(json.load(response), args.product, args.repository)
    gh('api', '--method', 'PUT', f'repos/{CENTRAL}/environments/{args.product}')
    title = 'vst-release-pipeline:' + args.product
    old_keys = json.loads(gh('api', f'repos/{args.repository}/keys'))
    with tempfile.TemporaryDirectory(prefix='vst-source-key-') as directory:
        key = Path(directory) / 'id_ed25519'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', title, '-f', str(key)], check=True)
        gh('repo', 'deploy-key', 'add', str(key) + '.pub', '--repo', args.repository, '--title', title)
        gh('secret', 'set', 'SOURCE_SSH_KEY', '--repo', CENTRAL, '--env', args.product, value=key.read_text())
    for old in old_keys:
        if old['title'] == title:
            gh('api', '--method', 'DELETE', f"repos/{args.repository}/keys/{old['id']}")
    storage = subprocess.check_output(['ssh', args.server, 'python3', '-', args.product],
                                      input=(ROOT / 'scripts/provision-storage.py').read_text(), text=True)
    credentials = json.loads(storage)
    for name, value in [('MINIO_ACCESS_KEY', credentials['access']), ('MINIO_SECRET_KEY', credentials['secret'])]:
        gh('secret', 'set', name, '--repo', CENTRAL, '--env', args.product, value=value)
    gh('secret', 'set', 'REGISTRY_TOKEN', '--repo', CENTRAL, value=token)
    products[args.product] = {'repository': args.repository}
    products_path.write_text(json.dumps(products, indent=2) + '\n')
    print(f'{args.product}: read-only source key, scoped storage credentials, and registry access configured.')
    print('Commit and push products.json before starting the central workflow.')


if __name__ == '__main__':
    main()
