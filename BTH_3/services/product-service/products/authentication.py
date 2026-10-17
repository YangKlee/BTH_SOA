"""Authenticate product requests through the Auth Service verification API."""

import json
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import APIException, AuthenticationFailed


class AuthServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Authentication service is unavailable."


class RemoteJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != b"bearer" or len(parts) != 2:
            raise AuthenticationFailed("Authorization header must be: Bearer <token>.")

        try:
            token = parts[1].decode("ascii")
        except UnicodeDecodeError as exc:
            raise AuthenticationFailed("Invalid bearer token.") from exc

        verify_request = Request(
            f"{settings.AUTH_SERVICE_URL}/token/verify/",
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        try:
            with urlopen(verify_request, timeout=settings.AUTH_SERVICE_TIMEOUT_SECONDS) as response:
                if response.status != 200:
                    raise AuthServiceUnavailable()
                payload = json.load(response)
        except HTTPError as exc:
            if exc.code == 401:
                raise AuthenticationFailed("Invalid or expired token.") from exc
            raise AuthServiceUnavailable() from exc
        except (URLError, TimeoutError, OSError, ValueError, UnicodeError) as exc:
            raise AuthServiceUnavailable() from exc

        if (
            not isinstance(payload, dict)
            or set(payload) != {"user_id", "email", "role"}
            or not isinstance(payload["user_id"], str)
            or not payload["user_id"].strip()
            or not isinstance(payload["email"], str)
            or not payload["email"].strip()
            or type(payload["role"]) is not int
        ):
            raise AuthServiceUnavailable()

        user = SimpleNamespace(
            userid=payload["user_id"],
            email=payload["email"],
            role=payload["role"],
            is_authenticated=True,
        )
        return user, token

    def authenticate_header(self, request):
        return "Bearer"
