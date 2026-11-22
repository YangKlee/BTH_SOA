"""Controlled domain errors with JSON values preserved in API responses."""

from rest_framework.exceptions import APIException


class OrderAPIError(APIException):
    def __init__(self, status_code, code, detail, **context):
        self.status_code = status_code
        self.detail = {"code": code, "detail": detail, **context}
