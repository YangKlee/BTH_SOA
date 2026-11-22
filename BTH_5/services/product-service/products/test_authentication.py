import io
import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.response import Response
from rest_framework.views import APIView


class ProtectedView(APIView):
    def get(self, request):
        return Response({"user_id": request.user.userid})


class FakeHTTPResponse(io.BytesIO):
    status = 200


@override_settings(
    AUTH_SERVICE_URL="http://auth.example:8000",
    AUTH_SERVICE_TIMEOUT_SECONDS=3,
)
class RemoteJWTAuthenticationTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ProtectedView.as_view()

    def request(self, authorization="Bearer access-token"):
        headers = {"HTTP_AUTHORIZATION": authorization} if authorization is not None else {}
        return self.view(self.factory.get("/products", **headers))

    @patch("products.authentication.urlopen")
    def test_valid_identity_is_accepted_for_each_request(self, urlopen):
        payload = {"user_id": "u-1", "email": "u@example.com", "role": 0}
        urlopen.side_effect = lambda *args, **kwargs: FakeHTTPResponse(
            json.dumps(payload).encode("utf-8")
        )

        self.assertEqual(self.request().status_code, 200)
        self.assertEqual(self.request().data, {"user_id": "u-1"})
        self.assertEqual(urlopen.call_count, 2)
        sent_request = urlopen.call_args.args[0]
        self.assertEqual(sent_request.full_url, "http://auth.example:8000/token/verify/")
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer access-token")
        self.assertEqual(sent_request.get_method(), "GET")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 3)

    @patch("products.authentication.urlopen")
    def test_missing_or_malformed_bearer_returns_401_without_http_call(self, urlopen):
        for header in (None, "Basic abc", "Bearer", "Bearer one two"):
            with self.subTest(header=header):
                response = self.request(header)
                self.assertEqual(response.status_code, 401)
                self.assertIn("detail", response.data)
        urlopen.assert_not_called()

    @patch("products.authentication.urlopen")
    def test_auth_401_returns_401(self, urlopen):
        urlopen.side_effect = HTTPError("http://auth.example", 401, "Unauthorized", {}, None)
        response = self.request()
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.data)

    @patch("products.authentication.urlopen")
    def test_timeout_connection_and_server_errors_return_503(self, urlopen):
        errors = (
            TimeoutError("timed out"),
            URLError("connection refused"),
            HTTPError("http://auth.example", 503, "Unavailable", {}, None),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                urlopen.side_effect = error
                response = self.request()
                self.assertEqual(response.status_code, 503)
                self.assertIn("detail", response.data)

    @patch("products.authentication.urlopen")
    def test_invalid_identity_payload_returns_503(self, urlopen):
        invalid = (
            b"not json",
            b"[]",
            b'{"user_id":"u-1","email":"u@example.com"}',
            b'{"user_id":"","email":"u@example.com","role":0}',
            b'{"user_id":"u-1","email":"u@example.com","role":true}',
        )
        for body in invalid:
            with self.subTest(body=body):
                urlopen.side_effect = None
                urlopen.return_value = FakeHTTPResponse(body)
                response = self.request()
                self.assertEqual(response.status_code, 503)
                self.assertIn("detail", response.data)

    @patch("products.authentication.urlopen")
    def test_unexpected_http_status_returns_503(self, urlopen):
        response = FakeHTTPResponse(b"{}")
        response.status = 204
        urlopen.return_value = response
        self.assertEqual(self.request().status_code, 503)
