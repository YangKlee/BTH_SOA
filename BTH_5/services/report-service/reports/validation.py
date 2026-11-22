"""Consistent URL, query-parameter, and JSON limits for Report Service."""

from datetime import date

from rest_framework.exceptions import ValidationError

SQLITE_MAX_INTEGER = 9223372036854775807
VALID_ORDER_STATUSES = frozenset({"pending", "completed", "cancelled"})


def parse_positive_id(raw, field_name="id"):
    if (
        not isinstance(raw, str)
        or not raw.isascii()
        or not raw.isdigit()
        or len(raw) > 19
    ):
        raise ValidationError({field_name: ["A positive integer id is required."]})
    value = int(raw)
    if not 0 < value <= SQLITE_MAX_INTEGER:
        raise ValidationError({field_name: ["A positive integer id is required."]})
    return value


def parse_optional_date(raw, field_name):
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str) or len(raw) != 10:
        raise ValidationError({field_name: ["Date must use YYYY-MM-DD format."]})
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError({field_name: ["Date must use YYYY-MM-DD format."]}) from exc


def parse_bool_param(raw, field_name, default=False):
    if raw is None or raw == "":
        return default
    if not isinstance(raw, str):
        raise ValidationError({field_name: ["Must be 'true' or 'false'."]})
    lowered = raw.strip().lower()
    if lowered in {"true", "1"}:
        return True
    if lowered in {"false", "0"}:
        return False
    raise ValidationError({field_name: ["Must be 'true' or 'false'."]})


def parse_report_filters(query_params, *, allow_status=False, allow_product_id=False):
    from_date = parse_optional_date(query_params.get("from_date"), "from_date")
    to_date = parse_optional_date(query_params.get("to_date"), "to_date")
    if from_date and to_date and from_date > to_date:
        raise ValidationError({"from_date": ["from_date cannot be later than to_date."]})

    include_pending = parse_bool_param(
        query_params.get("include_pending"), "include_pending", default=False
    )

    result = {
        "from_date": from_date,
        "to_date": to_date,
        "include_pending": include_pending,
    }

    if allow_status:
        raw_status = query_params.get("status")
        if raw_status is None or raw_status == "" or raw_status == "all":
            result["status"] = "all"
        elif raw_status in VALID_ORDER_STATUSES:
            result["status"] = raw_status
        else:
            raise ValidationError(
                {"status": ["Status must be one of: all, pending, completed, cancelled."]}
            )

    if allow_product_id:
        raw_product_id = query_params.get("product_id")
        if raw_product_id is None or raw_product_id == "":
            result["product_id"] = None
        else:
            result["product_id"] = parse_positive_id(raw_product_id, field_name="product_id")

    return result
