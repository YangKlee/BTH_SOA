import io
import json
from http.client import IncompleteRead
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.authentication import RemoteJWTAuthentication
from orders.clients.http import NoRedirectHandler, open_service


class ProtectedView(APIView):
    def get(self, request):
        return Response({"user_id": request.user.userid, "token": request.auth})


class FakeHTTPResponse(io.BytesIO):
    status = 200


@override_settings(
    AUTH_SERVICE_URL="http://auth.example:8000/",
    AUTH_SERVICE_TIMEOUT_SECONDS=2.5,
)
class RemoteJWTAuthenticationTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ProtectedView.as_view()
        self.identity = {"user_id": "u-1", "email": "u@example.com", "role": 0}

    def request(self, authorization="Bearer access-token"):
        headers = {"HTTP_AUTHORIZATION": authorization} if authorization is not None else {}
        return self.view(self.factory.get("/orders", **headers))

    @patch("orders.authentication.open_service")
    def test_valid_identity_is_verified_on_each_request_and_token_is_retained(self, transport):
        transport.side_effect = lambda *a, **kw: FakeHTTPResponse(json.dumps(self.identity).encode())
        for header in ("Bearer access-token", "bearer access-token"):
            response = self.request(header)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, {"user_id": "u-1", "token": "access-token"})
        self.assertEqual(transport.call_count, 2)
        sent = transport.call_args.args[0]
        self.assertEqual(sent.full_url, "http://auth.example:8000/token/verify/")
        self.assertEqual(sent.get_header("Authorization"), "Bearer access-token")
        self.assertEqual(sent.get_method(), "GET")
        self.assertEqual(transport.call_args.kwargs, {"timeout": 2.5})

    @patch("orders.authentication.open_service")
    def test_missing_and_malformed_header_return_401_without_calling_auth(self, transport):
        for header in (None, "", "Basic abc", "Bearer", "Bearer one two", "Bearer \u00f1"):
            with self.subTest(header=header):
                response = self.request(header)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response["WWW-Authenticate"], "Bearer")
                self.assertIn("detail", response.data)
        transport.assert_not_called()

    @patch("orders.authentication.open_service")
    def test_upstream_401_is_401(self, transport):
        transport.side_effect = HTTPError("http://auth.example", 401, "Unauthorized", {}, None)
        response = self.request()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["WWW-Authenticate"], "Bearer")

    @patch("orders.authentication.open_service")
    def test_unavailable_transport_and_unexpected_http_errors_are_503(self, transport):
        errors = [TimeoutError(), URLError("unreachable"), OSError(), IncompleteRead(b"x", 4)]
        errors += [HTTPError("http://auth.example", status, "upstream error", {}, None)
                   for status in (301, 302, 403, 404, 500, 503)]
        for error in errors:
            with self.subTest(error=repr(error)):
                transport.side_effect = error
                response = self.request()
                self.assertEqual(response.status_code, 503)
                self.assertEqual(set(response.data), {"detail"})

    @patch("orders.authentication.open_service")
    def test_invalid_json_or_identity_schema_returns_503(self, transport):
        bodies = [b"not json", b"\xff", b"[]", b"null"]
        for updates in (
            {"user_id": ""}, {"user_id": 1}, {"email": " "}, {"email": None},
            {"role": True}, {"role": "0"}, {"unexpected": "field"},
        ):
            bodies.append(json.dumps(self.identity | updates).encode())
        bodies.append(json.dumps({"user_id": "u-1", "email": "u@example.com"}).encode())
        for body in bodies:
            with self.subTest(body=body):
                transport.return_value = FakeHTTPResponse(body)
                response = self.request()
                self.assertEqual(response.status_code, 503)
                self.assertEqual(set(response.data), {"detail"})

    @patch("orders.authentication.open_service")
    def test_non_200_success_status_is_rejected(self, transport):
        upstream = FakeHTTPResponse(b"{}")
        upstream.status = 204
        transport.return_value = upstream
        self.assertEqual(self.request().status_code, 503)

    def test_default_authentication_is_remote_verifier(self):
        self.assertEqual(ProtectedView.authentication_classes, [RemoteJWTAuthentication])


class ServiceTransportTests(SimpleTestCase):
    def test_redirect_handler_refuses_to_build_followup_request(self):
        self.assertIsNone(NoRedirectHandler().redirect_request(
            None, None, 302, "Found", {}, "https://other.example/steal"
        ))

    @patch("orders.clients.http._opener.open")
    def test_transport_forwards_request_and_finite_timeout(self, opener):
        sentinel = object()
        open_service(sentinel, timeout=3)
        opener.assert_called_once_with(sentinel, timeout=3)
