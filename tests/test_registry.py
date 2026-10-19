import unittest
from registry import validate


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            'repository': 'edeori/StringLife-VST',
            'bucket': 'downloads',
            'mac_key': 'plugins/stringlife/mac/StringLife-Installer.pkg',
            'windows_key': 'plugins/stringlife/win/StringLife-Setup-Win.exe',
        }

    def test_registered_destinations(self):
        self.assertEqual(validate(self.config, 'stringlife', 'edeori/StringLife-VST')['mac_key'],
                         self.config['mac_key'])

    def test_wrong_repository_is_rejected(self):
        with self.assertRaises(ValueError):
            validate(self.config, 'stringlife', 'edeori/Other-VST')

    def test_untrusted_destinations_are_rejected(self):
        for key in ['plugins/other/mac/Installer.pkg', '../Installer.pkg',
                    'plugins/stringlife/mac/Installer.pkg\ninjected=output',
                    'plugins/stringlife/mac/Installer.exe',
                    'plugins/stringlife/mac/Installer-1.6.3.pkg']:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(dict(self.config, mac_key=key), 'stringlife', 'edeori/StringLife-VST')

    def test_wrong_bucket_is_rejected(self):
        with self.assertRaises(ValueError):
            validate(dict(self.config, bucket='private'), 'stringlife', 'edeori/StringLife-VST')


if __name__ == '__main__':
    unittest.main()
