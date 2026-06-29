import unittest

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.rate_limit import reset_local_rate_limits
from app.main import app


class RateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = get_settings()
        self.original_enabled = self.settings.rate_limit_enabled
        self.original_limit = self.settings.rate_limit_per_minute
        self.original_redis_url = self.settings.redis_url
        self.settings.rate_limit_enabled = True
        self.settings.rate_limit_per_minute = 1
        self.settings.redis_url = "redis://127.0.0.1:1/0"
        reset_local_rate_limits()

    def tearDown(self) -> None:
        self.settings.rate_limit_enabled = self.original_enabled
        self.settings.rate_limit_per_minute = self.original_limit
        self.settings.redis_url = self.original_redis_url
        reset_local_rate_limits()

    def test_rate_limiter_returns_429_after_limit(self) -> None:
        client = TestClient(app)

        first = client.get("/api/v1/auth/me")
        second = client.get("/api/v1/auth/me")

        self.assertEqual(first.status_code, 401, first.text)
        self.assertEqual(second.status_code, 429, second.text)
        self.assertEqual(second.headers["retry-after"], "60")


if __name__ == "__main__":
    unittest.main()
