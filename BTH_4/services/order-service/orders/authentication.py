"""Verify every Order request through the independent Auth Service."""

import json
from http.client import HTTPException
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.request import Request

from django.conf import settings
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import APIException, AuthenticationFailed

from orders.clients.http import open_service


class AuthServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Authentication service is unavailable."
    default_code = "auth_unavailable"


class RemoteJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if len(parts) != 2 or parts[0].lower() != b"bearer":
            raise AuthenticationFailed("Authorization header must be: Bearer <token>.")
        try:
            token = parts[1].decode("ascii")
        except UnicodeDecodeError as exc:
            raise AuthenticationFailed("Invalid bearer token.") from exc

        upstream = Request(
            f"{settings.AUTH_SERVICE_URL.rstrip('/')}/token/verify/",
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        try:
            with open_service(upstream, timeout=settings.AUTH_SERVICE_TIMEOUT_SECONDS) as response:
                if response.status != 200:
                    raise AuthServiceUnavailable()
                identity = json.load(response)
        except HTTPError as exc:
            if exc.code == 401:
                raise AuthenticationFailed("Invalid or expired token.") from exc
            raise AuthServiceUnavailable() from exc
        except (URLError, TimeoutError, OSError, ValueError, UnicodeError, HTTPException) as exc:
            raise AuthServiceUnavailable() from exc

        if (
            not isinstance(identity, dict)
            or set(identity) != {"user_id", "email", "role"}
            or not isinstance(identity["user_id"], str)
            or not identity["user_id"].strip()
            or not isinstance(identity["email"], str)
            or not identity["email"].strip()
            or type(identity["role"]) is not int
        ):
            raise AuthServiceUnavailable()

        return SimpleNamespace(
            userid=identity["user_id"],
            email=identity["email"],
            role=identity["role"],
            is_authenticated=True,
        ), token

    def authenticate_header(self, request):
        return "Bearer"
