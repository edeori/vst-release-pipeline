"""Keep reusable Apple credentials in the local Keychain and selected repo secrets."""
import argparse
import base64
import getpass
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--p12', type=Path, help='Export containing Developer ID Application and Installer identities')
parser.add_argument('--apple-id')
parser.add_argument('--team-id')
parser.add_argument('--repository', action='append', default=[], help='Repository to update; repeat for multiple VSTs')
args = parser.parse_args()
if args.p12:
    values = {'APPLE_CERTIFICATES_P12': base64.b64encode(args.p12.read_bytes()).decode(),
              'APPLE_CERTIFICATES_PASSWORD': getpass.getpass('P12 export password: ')}
else:
    values = json.loads(subprocess.check_output(['swift', str(ROOT / 'scripts/keychain-secrets.swift'), 'read']))
values['APPLE_ID'] = args.apple_id or values.get('APPLE_ID') or input('Apple ID: ').strip()
values['APPLE_TEAM_ID'] = args.team_id or values.get('APPLE_TEAM_ID') or input('Apple Team ID: ').strip()
values['APPLE_APP_PASSWORD'] = getpass.getpass('Apple app-specific password: ')
subprocess.run(['xcrun', 'notarytool', 'history', '--apple-id', values['APPLE_ID'],
                '--team-id', values['APPLE_TEAM_ID'], '--password', values['APPLE_APP_PASSWORD']],
               stdout=subprocess.DEVNULL, check=True)
subprocess.run(['swift', str(ROOT / 'scripts/keychain-secrets.swift'), 'store'],
               input=json.dumps(values), text=True, check=True)
for repository in args.repository:
    for name, value in values.items():
        subprocess.run(['gh', 'secret', 'set', name, '--repo', repository], input=value, text=True, check=True)
print('Apple credentials validated and saved in the local Keychain; selected repositories updated.')
