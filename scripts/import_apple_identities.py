"""Import multi-identity PKCS12 bundles reliably on modern macOS runners.

Some security import versions silently omit identities in combined bundles.
Match certificate/public-key pairs and import one encrypted PKCS12 per identity.
Plaintext private keys stay in process memory; no credential values are logged.
"""
import base64
import os
import re
import subprocess
import sys
import tempfile


def openssl(arguments, data):
    result = subprocess.run(['openssl', *arguments], input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('OpenSSL signing identity conversion failed')
    return result.stdout


def identity_bundles(pem):
    # OpenSSL bag attributes can contain non-UTF-8 localized friendly names.
    keys = re.findall(rb'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----', pem, re.S)
    certs = re.findall(rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', pem, re.S)
    public_keys = [openssl(['pkey', '-pubin', '-outform', 'DER'],
                          openssl(['x509', '-pubkey', '-noout'], cert)) for cert in certs]
    bundles, roles = [], set()
    for key in keys:
        public = openssl(['pkey', '-pubout', '-outform', 'DER'], key)
        for cert, certificate_public in zip(certs, public_keys):
            if public != certificate_public:
                continue
            subject = openssl(['x509', '-noout', '-subject'], cert)
            for role in (b'Developer ID Application:', b'Developer ID Installer:'):
                if role in subject:
                    roles.add(role)
            bundles.append(openssl(['pkcs12', '-export', '-name', 'CI signing identity',
                                    '-passout', 'env:CERTIFICATES_PASSWORD'], key + b'\n' + cert))
    if len(roles) != 2:
        raise RuntimeError('Both Developer ID Application and Installer identities require matching private keys')
    return bundles


def main():
    bundle = base64.b64decode(os.environ['CERTIFICATES'], validate=True)
    pem = openssl(['pkcs12', '-nodes', '-passin', 'env:CERTIFICATES_PASSWORD'], bundle)
    identities = identity_bundles(pem)
    for identity in identities:
        with tempfile.NamedTemporaryFile(suffix='.p12', dir=os.environ.get('RUNNER_TEMP')) as file:
            file.write(identity)
            file.flush()
            result = subprocess.run(['security', 'import', file.name, '-P', os.environ['CERTIFICATES_PASSWORD'],
                                     '-A', '-f', 'pkcs12', '-k', sys.argv[1]],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Never propagate CalledProcessError: its command would contain -P.
            if result.returncode:
                raise RuntimeError('Apple signing identity import failed')
    print(f'Imported {len(identities)} matched signing identities')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('Apple signing identity import failed; check the configured certificate bundle') from None
