from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .models import Users


class TokenVerifyTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = SimpleNamespace(
            userid="user-123",
            email="person@example.com",
            role=2,
            password=make_password("test-password"),
            is_authenticated=True,
        )

    def access_token(self):
        token = AccessToken()
        token["user_id"] = self.user.userid
        return token

    def verify(self, token):
        return self.client.get(
            "/token/verify/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

    @patch("authentication.authentication.Users.objects.get")
    def test_valid_access_token_returns_current_user_fields_only(self, get_user):
        get_user.return_value = self.user
        response = self.verify(self.access_token())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "user_id": "user-123",
            "email": "person@example.com",
            "role": 2,
        })
        get_user.assert_called_once_with(userid="user-123")

    def test_missing_bearer_header_returns_401(self):
        self.assertEqual(self.client.get("/token/verify/").status_code, 401)
        self.assertEqual(
            self.client.get(
                "/token/verify/", HTTP_AUTHORIZATION="Basic credentials"
            ).status_code,
            401,
        )

    def test_invalid_access_token_returns_401(self):
        self.assertEqual(self.verify("invalid.token.value").status_code, 401)

    def test_expired_access_token_returns_401(self):
        token = self.access_token()
        token.set_exp(
            from_time=timezone.now() - timedelta(days=2),
            lifetime=timedelta(days=1),
        )
        self.assertEqual(self.verify(token).status_code, 401)

    def test_refresh_token_returns_401(self):
        refresh = RefreshToken()
        refresh["user_id"] = self.user.userid
        self.assertEqual(self.verify(refresh).status_code, 401)

    @patch("authentication.authentication.Users.objects.get")
    def test_deleted_user_returns_401(self, get_user):
        get_user.side_effect = Users.DoesNotExist
        self.assertEqual(self.verify(self.access_token()).status_code, 401)

    @patch("authentication.views.Users.objects.get")
    @patch("authentication.authentication.Users.objects.get")
    def test_login_and_refresh_contract_remains_available(self, get_auth_user, get_user):
        get_user.return_value = self.user
        get_auth_user.return_value = self.user
        login = self.client.post(
            "/login/",
            {"identifier": self.user.email, "password": "test-password"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(set(login.json()), {"access", "refresh"})

        verified = self.verify(login.json()["access"])
        self.assertEqual(verified.status_code, 200)

        refreshed = self.client.post(
            "/token/refresh/", {"refresh": login.json()["refresh"]}, format="json"
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(set(refreshed.json()), {"access"})
        self.assertEqual(self.verify(refreshed.json()["access"]).status_code, 200)
