"""Consistent URL and JSON integer limits for SQLite."""
from rest_framework.exceptions import ValidationError

SQLITE_MAX_INTEGER = 9223372036854775807


def parse_positive_id(raw):
    if (
        not isinstance(raw, str)
        or not raw.isascii()
        or not raw.isdigit()
        or len(raw) > 19
    ):
        raise ValidationError({"id": ["A positive integer id is required."]})
    value = int(raw)
    if not 0 < value <= SQLITE_MAX_INTEGER:
        raise ValidationError({"id": ["A positive integer id is required."]})
    return value
