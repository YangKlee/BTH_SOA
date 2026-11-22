"""Verify remote JWT authentication and fail-closed behavior."""
import io
import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from rest_framework.test import APITestCase


def _json_response(payload, status=200):
    buf = io.BytesIO(json.dumps(payload).encode())
    buf.status = status
    return buf


class AuthenticationTests(APITestCase):
    def test_health_endpoint_is_public(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok", "service": "report-service"})

    def test_missing_or_malformed_authorization_rejected(self):
        for header in (None, "", "Token abc", "Bearer", "Bearer a b"):
            with self.subTest(header=header):
                if header is None:
                    self.client.credentials()
                else:
                    self.client.credentials(HTTP_AUTHORIZATION=header)
                response = self.client.get("/reports/summary")
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response["WWW-Authenticate"], "Bearer")

    def test_auth_service_401_maps_to_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer expired-token")
        err = HTTPError("http://127.0.0.1:8000/token/verify/", 401, "Unauthorized", {}, None)
        with patch("reports.authentication.open_service", side_effect=err):
            response = self.client.get("/reports/summary")
        self.assertEqual(response.status_code, 401)

    def test_auth_service_network_or_malformed_response_maps_to_503(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer good-token")
        for side_effect in (
            URLError("connection refused"),
            TimeoutError("timed out"),
            HTTPError("http://127.0.0.1:8000/token/verify/", 500, "Error", {}, None),
            lambda *a, **kw: _json_response({"user_id": "u1", "email": "a@b.com"}),
            lambda *a, **kw: _json_response({"user_id": "u1", "email": "a@b.com", "role": "1"}),
        ):
            with self.subTest(side_effect=side_effect):
                with patch("reports.authentication.open_service", side_effect=side_effect):
                    response = self.client.get("/reports/summary")
                self.assertEqual(response.status_code, 503)
