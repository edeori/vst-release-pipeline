import unittest
from resolve import resolve


class ResolveTests(unittest.TestCase):
    def test_registered_private_or_public_repository(self):
        self.assertEqual(resolve('phaselock', {'phaselock': {'repository': 'edeori/PhaseLock-VST'}}), 'edeori/PhaseLock-VST')

    def test_unknown_product_has_no_access(self):
        with self.assertRaises(KeyError):
            resolve('other', {'stringlife': {'repository': 'edeori/StringLife-VST'}})

    def test_untrusted_owner_and_output_injection(self):
        for repo in ['attacker/plugin', 'edeori/foo\ninjected=true', 'edeori/../other']:
            with self.subTest(repo=repo), self.assertRaises(ValueError):
                resolve('test', {'test': {'repository': repo}})

    def test_invalid_product_ids(self):
        for product in ['../foo', 'foo\nbar', 'foo/bar', '', '-foo']:
            with self.subTest(product=product), self.assertRaises(ValueError):
                resolve(product, {})
