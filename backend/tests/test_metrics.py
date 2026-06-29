import unittest

from fastapi.testclient import TestClient

from app.core.metrics import MetricsRegistry, metrics
from app.main import app


class MetricsTests(unittest.TestCase):
    def tearDown(self) -> None:
        metrics.reset()

    def test_registry_renders_prometheus_counters_and_summaries(self) -> None:
        registry = MetricsRegistry()

        registry.increment("docintel_jobs", status="ready")
        registry.increment("docintel_jobs", status="ready")
        registry.observe("docintel_job_duration", 1.25, status="ready")

        rendered = registry.render_prometheus()

        self.assertIn('docintel_jobs_total{status="ready"} 2', rendered)
        self.assertIn('docintel_job_duration_seconds_count{status="ready"} 1', rendered)
        self.assertIn('docintel_job_duration_seconds_sum{status="ready"} 1.25', rendered)

    def test_metrics_endpoint_exposes_http_request_metrics(self) -> None:
        metrics.reset()
        client = TestClient(app)

        health = client.get("/health")
        self.assertEqual(health.status_code, 200, health.text)

        response = client.get("/metrics")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["content-type"], "text/plain; version=0.0.4; charset=utf-8")
        self.assertIn('docintel_http_requests_total{method="GET",path="/health",status_code="200"} 1', response.text)
        self.assertIn('docintel_http_request_duration_seconds_count{method="GET",path="/health",status_code="200"} 1', response.text)


if __name__ == "__main__":
    unittest.main()
