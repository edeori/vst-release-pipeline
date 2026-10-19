"""Run over SSH on mothstack; return credentials only to the provisioning process."""
import json
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

product = sys.argv[1]
if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', product):
    raise ValueError('Invalid product ID')
container = json.loads(subprocess.check_output(['docker', 'inspect', 'mothproduction-minio']))[0]
env = dict(item.split('=', 1) for item in container['Config']['Env'])
with tempfile.TemporaryDirectory(prefix='vst-ci-') as directory:
    config = Path(directory)
    (config / 'config.json').write_text(json.dumps({'version': '10', 'aliases': {'moth': {
        'url': 'http://mothproduction-minio:9000', 'accessKey': env['MINIO_ROOT_USER'],
        'secretKey': env['MINIO_ROOT_PASSWORD'], 'api': 'S3v4', 'path': 'auto'}}}))
    (config / 'config.json').chmod(0o600)
    policy = {'Version': '2012-10-17', 'Statement': [
        {'Effect': 'Allow', 'Action': ['s3:GetBucketLocation', 's3:ListBucketMultipartUploads'],
         'Resource': ['arn:aws:s3:::downloads']},
        {'Effect': 'Allow', 'Action': ['s3:GetObject', 's3:PutObject', 's3:AbortMultipartUpload', 's3:ListMultipartUploadParts'],
         'Resource': [f'arn:aws:s3:::downloads/{kind}/{product}/*' for kind in ('plugins', 'apps')]}
    ]}
    (config / 'policy.json').write_text(json.dumps(policy))
    def mc(*args):
        result = subprocess.run(['docker', 'run', '--rm', '--network', 'proxy', '-v', directory + ':/root/.mc',
                                 'minio/mc', *args], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if result.returncode:
            # Never include the command: user-add arguments contain a credential.
            raise RuntimeError('MinIO provisioning failed; inspect the server configuration')
    name = 'vst-ci-' + product
    password = secrets.token_urlsafe(36)
    mc('admin', 'policy', 'create', 'moth', name, '/root/.mc/policy.json')
    mc('admin', 'user', 'add', 'moth', name, password)
    mc('admin', 'policy', 'attach', 'moth', name, '--user', name)
    print(json.dumps({'access': name, 'secret': password}))
