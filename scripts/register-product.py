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
        description: Request production approval after both builds succeed
        type: boolean
        default: false
  push:
    branches: [main]
    tags: ['v*']
permissions:
  contents: write
jobs:
  release:
    uses: ''' + PIPELINE + '/.github/workflows/vst-release.yml@' + revision + '''
    with:
      product-id: ''' + product + '''
      publish: ${{ startsWith(github.ref, 'refs/tags/v') || inputs.publish }}
    secrets:
''' + ''.join('      ' + name + ': ${{ secrets.' + name + ' }}\n' for name in SECRET_NAMES)


def separate_callers(product, revision):
    build = caller(product, revision)
    begin = build.index('  workflow_dispatch:')
    end = build.index('  push:', begin)
    build = build[:begin] + '  workflow_dispatch:\n' + build[end:]
    build = build.replace('name: Release installers', 'name: Build installers')
    build = build.replace("publish: ${{ startsWith(github.ref, 'refs/tags/v') || inputs.publish }}", 'publish: false')
    build = ''.join(line for line in build.splitlines(keepends=True) if 'MINIO_' not in line)
    publish = """name: Publish installers
on:
  workflow_dispatch:
    inputs:
      build_selection:
        description: Which build to publish
        type: choice
        default: Latest successful build
        options:
          - Latest successful build
          - Specific build ID
      build_run_id:
        description: Only for Specific build ID; leave empty for latest successful default-branch build
        required: false
        type: string
      verify_only:
        description: Check the build and files without uploading
        type: boolean
        default: false
permissions:
  contents: read
  actions: read
jobs:
  publish:
    uses: """ + PIPELINE + '/.github/workflows/vst-publish.yml@' + revision + """
    with:
      product-id: """ + product + """
      build-selection: ${{ inputs.build_selection == 'Specific build ID' && 'specific' || 'latest' }}
      build-run-id: ${{ inputs.build_run_id }}
      verify-only: ${{ inputs.verify_only }}
    secrets:
""" + ''.join('      ' + name + ': ${{ secrets.' + name + ' }}\n' for name in
              ('REGISTRY_TOKEN', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY'))
    return build, publish


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('product')
    parser.add_argument('repository')
    parser.add_argument('--checkout', required=True, type=Path)
    parser.add_argument('--server', default='mothstack')
    parser.add_argument('--publication-mode', choices=('gated', 'separate'), default='gated')
    args = parser.parse_args()
    if not re.fullmatch(r'edeori/[A-Za-z0-9_.-]+', args.repository):
        raise ValueError('Expected an edeori source repository')
    revision = gh('api', f'repos/{PIPELINE}/commits/main', '--jq', '.sha').strip()
    contents = caller(args.product, revision)
    publish_contents = None
    if args.publication_mode == 'separate':
        contents, publish_contents = separate_callers(args.product, revision)
    target = args.checkout.resolve() / '.github/workflows/release.yml'
    if target.exists() and target.read_text() != contents:
        raise ValueError('Caller workflow already exists; review and update it manually')
    publish_target = target.with_name('publish.yml')
    if publish_contents and publish_target.exists() and publish_target.read_text() != publish_contents:
        raise ValueError('Publish workflow already exists; review manually')
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
    if args.publication_mode == 'gated':
        reviewer = json.loads(gh('api', 'user'))
        protection = {'wait_timer': 0, 'prevent_self_review': False,
                      'reviewers': [{'type': 'User', 'id': reviewer['id']}], 'can_admins_bypass': False}
        try:
            environment = json.loads(gh('api', '--method', 'PUT',
                f'repos/{args.repository}/environments/production', '--input', '-', value=json.dumps(protection)))
        except subprocess.CalledProcessError:
            raise SystemExit('Could not configure required publish reviewers. Check GitHub plan support (especially for private repositories); no release credentials were changed.') from None
        rules = environment.get('protection_rules', [])
        if not any(rule.get('type') == 'required_reviewers' and rule.get('reviewers') for rule in rules):
            raise SystemExit('Required publish reviewer was not configured; refusing unprotected publication setup.')
    storage = subprocess.check_output(['ssh', args.server, 'python3', '-', args.product],
                                      input=(ROOT / 'scripts/provision-storage.py').read_text(), text=True)
    credentials = json.loads(storage)
    values = {name: shared[name] for name in apple_names}
    values.update(REGISTRY_TOKEN=token, MINIO_ACCESS_KEY=credentials['access'], MINIO_SECRET_KEY=credentials['secret'])
    for name, value in values.items():
        gh('secret', 'set', name, '--repo', args.repository, value=value)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(contents)
    if publish_contents:
        publish_target.write_text(publish_contents)
    print(f'{args.repository}: caller workflow and repository secrets configured.')
    print('Review, commit and push the caller and adapters in the VST repository. Run Actions there.')


if __name__ == '__main__':
    main()
