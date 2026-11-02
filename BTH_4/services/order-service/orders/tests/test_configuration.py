"""Exercise startup validation in isolated processes without exposing env values."""
import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class ConfigurationTests(SimpleTestCase):
    def run_settings(self, **overrides):
        env = os.environ.copy()
        for key in ("ORDER_DEBUG", "ORDER_SECRET_KEY", "AUTH_SERVICE_TIMEOUT_SECONDS", "PRODUCT_SERVICE_TIMEOUT_SECONDS"):
            env.pop(key, None)
        env.update(overrides)
        return subprocess.run(
            [sys.executable, "-c", "import config.settings as s; print(s.DATABASES['default']['NAME'])"],
            cwd=Path(__file__).resolve().parents[2], env=env, capture_output=True, text=True,
        )

    def test_default_settings_start_and_database_is_separate(self):
        result = self.run_settings()
        self.assertEqual(result.returncode, 0, result.stderr)
        from django.conf import settings
        self.assertEqual(Path(result.stdout.strip()).name, "orders.sqlite3")
        self.assertEqual(settings.DATABASES["default"]["OPTIONS"]["transaction_mode"], "IMMEDIATE")
        self.assertFalse(settings.DATABASES["default"].get("ATOMIC_REQUESTS", False))

    def test_production_requires_explicit_secret(self):
        result = self.run_settings(ORDER_DEBUG="false")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ORDER_SECRET_KEY is required", result.stderr)
        self.assertEqual(self.run_settings(ORDER_DEBUG="false", ORDER_SECRET_KEY="test-only-key").returncode, 0)

    def test_timeouts_must_be_finite_positive_numbers(self):
        for key in ("AUTH_SERVICE_TIMEOUT_SECONDS", "PRODUCT_SERVICE_TIMEOUT_SECONDS"):
            for value in ("0", "-1", "nan", "inf", "abc"):
                with self.subTest(key=key, value=value):
                    result = self.run_settings(**{key: value})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("positive finite number", result.stderr)
