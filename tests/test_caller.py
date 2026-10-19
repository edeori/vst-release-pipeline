import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('register_product', Path(__file__).resolve().parents[1] / 'scripts/register-product.py')
register = importlib.util.module_from_spec(spec)
spec.loader.exec_module(register)


class CallerTests(unittest.TestCase):
    def test_caller_uses_shared_workflow_and_explicit_secrets(self):
        text = register.caller('phaselock', 'a' * 40)
        self.assertIn('product-id: phaselock', text)
        self.assertIn('vst-release.yml@' + 'a' * 40, text)
        self.assertIn("tags: ['v*']", text)
        self.assertIn("github.event_name == 'push' || inputs.publish", text)
        for name in register.SECRET_NAMES:
            self.assertIn(name + ': ${{ secrets.' + name + ' }}', text)

    def test_rejects_product_and_revision_injection(self):
        for product, revision in [('bad\ninjected: true', 'a' * 40), ('test', 'main'), ('test', 'a' * 40 + '\n')]:
            with self.subTest(product=product, revision=revision), self.assertRaises(ValueError):
                register.caller(product, revision)
