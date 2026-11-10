import unittest
from unittest.mock import patch
import import_apple_identities as identities


def cert(name):
    return b'-----BEGIN CERTIFICATE-----\n' + name + b'\n-----END CERTIFICATE-----'


def key(name):
    return b'-----BEGIN PRIVATE KEY-----\n' + name + b'\n-----END PRIVATE KEY-----'


class AppleIdentitiesTests(unittest.TestCase):
    def convert(self, args, data):
        if args[:3] == ['x509', '-pubkey', '-noout']:
            return b'app' if b'APP' in data else b'installer'
        if args[0] == 'pkey':
            if args[1] == '-pubin':
                return data
            return b'app' if b'APP' in data else b'installer'
        if args[:3] == ['x509', '-noout', '-subject']:
            return b'Developer ID Application:' if b'APP' in data else b'Developer ID Installer:'
        if args[:2] == ['pkcs12', '-export']:
            self.assertIn('env:CERTIFICATES_PASSWORD', args)
            return b'encrypted-bundle'
        self.fail('Unexpected OpenSSL operation')

    def test_combined_bundle_with_localized_attributes(self):
        pem = b'friendlyName: M\xe1rton\n' + key(b'APP') + cert(b'APP') + key(b'INSTALLER') + cert(b'INSTALLER')
        with patch.object(identities, 'openssl', side_effect=self.convert):
            self.assertEqual(identities.identity_bundles(pem), [b'encrypted-bundle'] * 2)

    def test_missing_installer_key_rejected(self):
        pem = key(b'APP') + cert(b'APP') + cert(b'INSTALLER')
        with patch.object(identities, 'openssl', side_effect=self.convert):
            with self.assertRaisesRegex(RuntimeError, 'matching private keys'):
                identities.identity_bundles(pem)

    def test_certificate_only_bundle_rejected(self):
        with patch.object(identities, 'openssl', side_effect=self.convert):
            with self.assertRaises(RuntimeError):
                identities.identity_bundles(cert(b'APP') + cert(b'INSTALLER'))

    def test_openssl_failure_does_not_expose_payload(self):
        with patch.object(identities.subprocess, 'run') as run:
            run.return_value.returncode = 1
            run.return_value.stderr = b'sensitive input'
            with self.assertRaisesRegex(RuntimeError, '^OpenSSL signing identity conversion failed$'):
                identities.openssl(['pkcs12'], b'private key data')
