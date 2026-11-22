"""Business logic for Report Service: cost management, live aggregation, and persisted snapshots."""

from collections import defaultdict
from contextlib import contextmanager
from decimal import Decimal, ROUND_HALF_UP

from django.db import IntegrityError, OperationalError, transaction

from reports.clients.order import get_order, list_order_items, list_orders
from reports.clients.product import get_product, list_products
from reports.errors import ReportAPIError
from reports.models import (
    OrderCost,
    OrderReportLine,
    ProductCost,
    ProductReportLine,
    ReportSnapshot,
)


ZERO = Decimal("0.00")
CENT = Decimal("0.01")
HUNDRED = Decimal("100")
MAX_REPORT_AMOUNT = Decimal("999999999999.99")


@contextmanager
def write_transaction():
    # SQLite's configured IMMEDIATE transaction acquires its write lock before
    # reading mutable state. Never issue HTTP from within this block.
    try:
        with transaction.atomic():
            yield
    except OperationalError as exc:
        if "locked" in str(exc).lower() or "busy" in str(exc).lower():
            raise ReportAPIError(
                503, "database_busy", "Report database is busy. Please try again."
            ) from exc
        raise
    except IntegrityError as exc:
        raise ReportAPIError(
            409, "data_conflict", "The record already exists or violates a data constraint."
        ) from exc


def _money(value, *, allow_negative=False):
    if not value.is_finite():
        raise ReportAPIError(400, "amount_overflow", "Computed monetary amount is not finite.")
    quantized = value.quantize(CENT, rounding=ROUND_HALF_UP)
    if not allow_negative and quantized < ZERO:
        raise ReportAPIError(400, "amount_overflow", "Computed monetary amount cannot be negative.")
    if abs(quantized) > MAX_REPORT_AMOUNT:
        raise ReportAPIError(400, "amount_overflow", "Computed monetary amount exceeds DECIMAL(14,2).")
    return quantized


def _fmt_money(value):
    return f"{value:.2f}"


def _profit_margin(profit, revenue):
    if revenue <= ZERO:
        return None
    margin = ((profit / revenue) * HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP)
    return f"{margin:.2f}"


def _fmt_iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def _in_date_range(dt, from_date, to_date):
    order_date = dt.date()
    if from_date is not None and order_date < from_date:
        return False
    if to_date is not None and order_date > to_date:
        return False
    return True


def _load_cost_maps():
    product_costs = {
        product_id: unit_cost
        for product_id, unit_cost in ProductCost.objects.values_list("product_id", "unit_cost")
    }
    order_costs = {
        order_id: additional_cost
        for order_id, additional_cost in OrderCost.objects.values_list("order_id", "additional_cost")
    }
    return product_costs, order_costs


# ---------------------------------------------------------------------------
# Cost Management (local database: reports.sqlite3, validated over HTTP)
# ---------------------------------------------------------------------------

def create_product_cost(data, token):
    product_id = data["product_id"]
    if ProductCost.objects.filter(product_id=product_id).exists():
        raise ReportAPIError(
            409, "product_cost_exists", "Cost configuration already exists for this product.", product_id=product_id
        )
    get_product(product_id, token, missing_status=400)
    with write_transaction():
        if ProductCost.objects.filter(product_id=product_id).exists():
            raise ReportAPIError(
                409,
                "product_cost_exists",
                "Cost configuration already exists for this product.",
                product_id=product_id,
            )
        return ProductCost.objects.create(
            product_id=product_id,
            unit_cost=data["unit_cost"],
            note=data.get("note", ""),
        )


def update_product_cost(product_id, data):
    with write_transaction():
        cost = ProductCost.objects.filter(product_id=product_id).first()
        if cost is None:
            raise ReportAPIError(
                404, "product_cost_not_found", "Product cost configuration not found.", product_id=product_id
            )
        cost.unit_cost = data["unit_cost"]
        cost.note = data.get("note", "")
        cost.save(update_fields=["unit_cost", "note", "updated_at"])
        return cost


def delete_product_cost(product_id):
    with write_transaction():
        deleted, _ = ProductCost.objects.filter(product_id=product_id).delete()
        if deleted == 0:
            raise ReportAPIError(
                404, "product_cost_not_found", "Product cost configuration not found.", product_id=product_id
            )


def create_order_cost(data, token):
    order_id = data["order_id"]
    if OrderCost.objects.filter(order_id=order_id).exists():
        raise ReportAPIError(
            409, "order_cost_exists", "Cost configuration already exists for this order.", order_id=order_id
        )
    get_order(order_id, token, missing_status=400)
    with write_transaction():
        if OrderCost.objects.filter(order_id=order_id).exists():
            raise ReportAPIError(
                409, "order_cost_exists", "Cost configuration already exists for this order.", order_id=order_id
            )
        return OrderCost.objects.create(
            order_id=order_id,
            additional_cost=data["additional_cost"],
            note=data.get("note", ""),
        )


def update_order_cost(order_id, data):
    with write_transaction():
        cost = OrderCost.objects.filter(order_id=order_id).first()
        if cost is None:
            raise ReportAPIError(
                404, "order_cost_not_found", "Order cost configuration not found.", order_id=order_id
            )
        cost.additional_cost = data["additional_cost"]
        cost.note = data.get("note", "")
        cost.save(update_fields=["additional_cost", "note", "updated_at"])
        return cost


def delete_order_cost(order_id):
    with write_transaction():
        deleted, _ = OrderCost.objects.filter(order_id=order_id).delete()
        if deleted == 0:
            raise ReportAPIError(
                404, "order_cost_not_found", "Order cost configuration not found.", order_id=order_id
            )


# ---------------------------------------------------------------------------
# Core Aggregation Engine
# ---------------------------------------------------------------------------

def _build_order_record(order, items, product_costs, order_costs, counted_statuses):
    is_counted = order.status in counted_statuses
    total_quantity = 0
    item_entries = []
    revenue = ZERO
    product_cost = ZERO

    for item in items:
        total_quantity += item.quantity
        unit_cost = product_costs.get(item.product_id, ZERO)
        if is_counted:
            item_revenue = _money(item.total_price)
            item_cost = _money(unit_cost * item.quantity)
            item_profit = _money(item_revenue - item_cost, allow_negative=True)
        else:
            item_revenue = ZERO
            item_cost = ZERO
            item_profit = ZERO
        revenue = _money(revenue + item_revenue)
        product_cost = _money(product_cost + item_cost)
        item_entries.append(
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": _fmt_money(item.unit_price),
                "unit_cost": _fmt_money(unit_cost),
                "cost_configured": item.product_id in product_costs,
                "revenue": _fmt_money(item_revenue),
                "cost": _fmt_money(item_cost),
                "profit": _fmt_money(item_profit),
            }
        )

    if is_counted and not items and order.total_amount > ZERO:
        revenue = _money(order.total_amount)

    sold_quantity = total_quantity if is_counted else 0
    additional_cost = _money(order_costs.get(order.id, ZERO)) if is_counted else ZERO
    total_cost = _money(product_cost + additional_cost)
    profit = _money(revenue - total_cost, allow_negative=True)

    return {
        "order_id": order.id,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "status": order.status,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "item_count": len(items),
        "total_quantity": total_quantity,
        "sold_quantity": sold_quantity,
        "order_total_amount": order.total_amount,
        "revenue": revenue,
        "product_cost": product_cost,
        "additional_cost": additional_cost,
        "total_cost": total_cost,
        "profit": profit,
        "items": item_entries,
        "product_ids": {item.product_id for item in items},
    }


def _compute_dataset(token, *, from_date=None, to_date=None, include_pending=False):
    products = list_products(token)
    orders = list_orders(token)
    order_items = list_order_items(token)
    product_costs, order_costs = _load_cost_maps()

    counted_statuses = {"completed", "pending"} if include_pending else {"completed"}

    filtered_orders = [
        order for order in orders if _in_date_range(order.created_at, from_date, to_date)
    ]

    items_by_order = defaultdict(list)
    for item in order_items:
        items_by_order[item.order_id].append(item)

    # Per-order breakdown
    order_records = [
        _build_order_record(
            order,
            items_by_order.get(order.id, []),
            product_costs,
            order_costs,
            counted_statuses,
        )
        for order in filtered_orders
    ]

    # Per-product aggregation from counted orders
    sold_by_product = defaultdict(int)
    revenue_by_product = defaultdict(lambda: ZERO)
    cost_by_product = defaultdict(lambda: ZERO)
    orders_by_product = defaultdict(set)
    fallback_name_by_product = {}

    for order in filtered_orders:
        if order.status not in counted_statuses:
            continue
        for item in items_by_order.get(order.id, []):
            unit_cost = product_costs.get(item.product_id, ZERO)
            sold_by_product[item.product_id] += item.quantity
            revenue_by_product[item.product_id] = _money(
                revenue_by_product[item.product_id] + item.total_price
            )
            cost_by_product[item.product_id] = _money(
                cost_by_product[item.product_id] + _money(unit_cost * item.quantity)
            )
            orders_by_product[item.product_id].add(order.id)
            fallback_name_by_product[item.product_id] = item.product_name

    catalog_by_id = {product.id: product for product in products}
    all_product_ids = sorted(set(catalog_by_id) | set(sold_by_product))

    product_records = []
    for product_id in all_product_ids:
        catalog_product = catalog_by_id.get(product_id)
        in_catalog = catalog_product is not None
        unit_cost = product_costs.get(product_id, ZERO)
        cost_configured = product_id in product_costs

        if in_catalog:
            product_name = catalog_product.name
            unit_price = catalog_product.price
            stock_quantity = catalog_product.quantity
            inventory_value = _money(unit_price * stock_quantity)
        else:
            product_name = fallback_name_by_product[product_id]
            unit_price = None
            stock_quantity = 0
            inventory_value = ZERO

        inventory_cost_value = _money(unit_cost * stock_quantity)
        sold_quantity = sold_by_product.get(product_id, 0)
        revenue = revenue_by_product.get(product_id, ZERO)
        cost = cost_by_product.get(product_id, ZERO)
        profit = _money(revenue - cost, allow_negative=True)

        product_records.append(
            {
                "product_id": product_id,
                "product_name": product_name,
                "in_catalog": in_catalog,
                "unit_price": unit_price,
                "unit_cost": unit_cost,
                "cost_configured": cost_configured,
                "stock_quantity": stock_quantity,
                "sold_quantity": sold_quantity,
                "order_count": len(orders_by_product.get(product_id, ())),
                "inventory_value": inventory_value,
                "inventory_cost_value": inventory_cost_value,
                "revenue": revenue,
                "cost": cost,
                "profit": profit,
            }
        )

    return product_records, order_records


def _serialize_product_record(rec):
    return {
        "product_id": rec["product_id"],
        "product_name": rec["product_name"],
        "in_catalog": rec["in_catalog"],
        "unit_price": _fmt_money(rec["unit_price"]) if rec["unit_price"] is not None else None,
        "unit_cost": _fmt_money(rec["unit_cost"]),
        "cost_configured": rec["cost_configured"],
        "stock_quantity": rec["stock_quantity"],
        "sold_quantity": rec["sold_quantity"],
        "order_count": rec["order_count"],
        "inventory_value": _fmt_money(rec["inventory_value"]),
        "inventory_cost_value": _fmt_money(rec["inventory_cost_value"]),
        "revenue": _fmt_money(rec["revenue"]),
        "cost": _fmt_money(rec["cost"]),
        "profit": _fmt_money(rec["profit"]),
        "profit_margin_percent": _profit_margin(rec["profit"], rec["revenue"]),
    }


def _serialize_order_record(rec):
    return {
        "order_id": rec["order_id"],
        "customer_name": rec["customer_name"],
        "customer_email": rec["customer_email"],
        "status": rec["status"],
        "created_at": _fmt_iso(rec["created_at"]),
        "updated_at": _fmt_iso(rec["updated_at"]),
        "item_count": rec["item_count"],
        "total_quantity": rec["total_quantity"],
        "sold_quantity": rec["sold_quantity"],
        "order_total_amount": _fmt_money(rec["order_total_amount"]),
        "revenue": _fmt_money(rec["revenue"]),
        "product_cost": _fmt_money(rec["product_cost"]),
        "additional_cost": _fmt_money(rec["additional_cost"]),
        "total_cost": _fmt_money(rec["total_cost"]),
        "profit": _fmt_money(rec["profit"]),
        "profit_margin_percent": _profit_margin(rec["profit"], rec["revenue"]),
        "items": rec["items"],
    }


def _summarize(product_records, order_records, include_pending):
    counted_statuses = {"completed", "pending"} if include_pending else {"completed"}

    in_stock_products = sum(1 for p in product_records if p["in_catalog"] and p["stock_quantity"] > 0)
    out_of_stock_products = sum(1 for p in product_records if p["in_catalog"] and p["stock_quantity"] == 0)
    total_stock_quantity = sum(p["stock_quantity"] for p in product_records)
    total_inventory_value = _money(sum((p["inventory_value"] for p in product_records), ZERO))
    total_inventory_cost_value = _money(sum((p["inventory_cost_value"] for p in product_records), ZERO))

    completed_orders = sum(1 for o in order_records if o["status"] == "completed")
    pending_orders = sum(1 for o in order_records if o["status"] == "pending")
    cancelled_orders = sum(1 for o in order_records if o["status"] == "cancelled")
    counted_orders = sum(1 for o in order_records if o["status"] in counted_statuses)

    total_sold_quantity = sum(o["sold_quantity"] for o in order_records)
    total_revenue = _money(sum((o["revenue"] for o in order_records), ZERO))
    total_product_cost = _money(sum((o["product_cost"] for o in order_records), ZERO))
    total_additional_cost = _money(sum((o["additional_cost"] for o in order_records), ZERO))
    total_cost = _money(total_product_cost + total_additional_cost)
    total_profit = _money(total_revenue - total_cost, allow_negative=True)

    return {
        "total_products": len(product_records),
        "in_stock_products": in_stock_products,
        "out_of_stock_products": out_of_stock_products,
        "total_stock_quantity": total_stock_quantity,
        "total_inventory_value": total_inventory_value,
        "total_inventory_cost_value": total_inventory_cost_value,
        "total_orders": len(order_records),
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
        "cancelled_orders": cancelled_orders,
        "counted_orders": counted_orders,
        "total_sold_quantity": total_sold_quantity,
        "total_revenue": total_revenue,
        "total_product_cost": total_product_cost,
        "total_additional_cost": total_additional_cost,
        "total_cost": total_cost,
        "total_profit": total_profit,
    }


def _filters_payload(from_date, to_date, include_pending, **extra):
    payload = {
        "from_date": from_date.isoformat() if from_date else None,
        "to_date": to_date.isoformat() if to_date else None,
        "include_pending": include_pending,
    }
    payload.update(extra)
    return payload


# ---------------------------------------------------------------------------
# Live Report Builders
# ---------------------------------------------------------------------------

def build_summary_report(token, *, from_date=None, to_date=None, include_pending=False):
    product_records, order_records = _compute_dataset(
        token, from_date=from_date, to_date=to_date, include_pending=include_pending
    )
    stats = _summarize(product_records, order_records, include_pending)
    return {
        "filters": _filters_payload(from_date, to_date, include_pending),
        "inventory": {
            "total_products": stats["total_products"],
            "in_stock_products": stats["in_stock_products"],
            "out_of_stock_products": stats["out_of_stock_products"],
            "total_stock_quantity": stats["total_stock_quantity"],
            "total_inventory_value": _fmt_money(stats["total_inventory_value"]),
            "total_inventory_cost_value": _fmt_money(stats["total_inventory_cost_value"]),
        },
        "sales": {
            "total_orders": stats["total_orders"],
            "completed_orders": stats["completed_orders"],
            "pending_orders": stats["pending_orders"],
            "cancelled_orders": stats["cancelled_orders"],
            "counted_orders": stats["counted_orders"],
            "total_sold_quantity": stats["total_sold_quantity"],
        },
        "financials": {
            "total_revenue": _fmt_money(stats["total_revenue"]),
            "total_product_cost": _fmt_money(stats["total_product_cost"]),
            "total_additional_cost": _fmt_money(stats["total_additional_cost"]),
            "total_cost": _fmt_money(stats["total_cost"]),
            "total_profit": _fmt_money(stats["total_profit"]),
            "profit_margin_percent": _profit_margin(stats["total_profit"], stats["total_revenue"]),
        },
    }


def build_products_report(token, *, from_date=None, to_date=None, include_pending=False, product_id=None):
    product_records, _ = _compute_dataset(
        token, from_date=from_date, to_date=to_date, include_pending=include_pending
    )
    if product_id is not None:
        product_records = [rec for rec in product_records if rec["product_id"] == product_id]

    total_stock = sum(p["stock_quantity"] for p in product_records)
    total_sold = sum(p["sold_quantity"] for p in product_records)
    total_inv_value = _money(sum((p["inventory_value"] for p in product_records), ZERO))
    total_inv_cost = _money(sum((p["inventory_cost_value"] for p in product_records), ZERO))
    total_revenue = _money(sum((p["revenue"] for p in product_records), ZERO))
    total_cost = _money(sum((p["cost"] for p in product_records), ZERO))
    total_profit = _money(total_revenue - total_cost, allow_negative=True)

    return {
        "filters": _filters_payload(from_date, to_date, include_pending, product_id=product_id),
        "totals": {
            "product_count": len(product_records),
            "total_stock_quantity": total_stock,
            "total_sold_quantity": total_sold,
            "total_inventory_value": _fmt_money(total_inv_value),
            "total_inventory_cost_value": _fmt_money(total_inv_cost),
            "total_revenue": _fmt_money(total_revenue),
            "total_cost": _fmt_money(total_cost),
            "total_profit": _fmt_money(total_profit),
            "profit_margin_percent": _profit_margin(total_profit, total_revenue),
        },
        "products": [_serialize_product_record(rec) for rec in product_records],
    }


def build_single_product_report(product_id, token, *, from_date=None, to_date=None, include_pending=False):
    catalog_product = get_product(product_id, token, allow_missing=True)
    orders = list_orders(token)
    order_items = list_order_items(token)
    product_costs, _ = _load_cost_maps()

    counted_statuses = {"completed", "pending"} if include_pending else {"completed"}
    counted_order_ids = {
        order.id
        for order in orders
        if order.status in counted_statuses and _in_date_range(order.created_at, from_date, to_date)
    }

    unit_cost = product_costs.get(product_id, ZERO)
    cost_configured = product_id in product_costs

    sold_quantity = 0
    revenue = ZERO
    cost = ZERO
    matching_orders = set()
    fallback_name = None

    for item in order_items:
        if item.product_id != product_id or item.order_id not in counted_order_ids:
            continue
        sold_quantity += item.quantity
        revenue = _money(revenue + item.total_price)
        cost = _money(cost + _money(unit_cost * item.quantity))
        matching_orders.add(item.order_id)
        fallback_name = item.product_name

    if catalog_product is None and fallback_name is None:
        raise ReportAPIError(
            404, "product_not_found", "Product not found in catalog or sales history.", product_id=product_id
        )

    in_catalog = catalog_product is not None
    if in_catalog:
        product_name = catalog_product.name
        unit_price = catalog_product.price
        stock_quantity = catalog_product.quantity
        inventory_value = _money(unit_price * stock_quantity)
    else:
        product_name = fallback_name
        unit_price = None
        stock_quantity = 0
        inventory_value = ZERO

    inventory_cost_value = _money(unit_cost * stock_quantity)
    profit = _money(revenue - cost, allow_negative=True)

    return {
        "filters": _filters_payload(from_date, to_date, include_pending),
        "product": _serialize_product_record(
            {
                "product_id": product_id,
                "product_name": product_name,
                "in_catalog": in_catalog,
                "unit_price": unit_price,
                "unit_cost": unit_cost,
                "cost_configured": cost_configured,
                "stock_quantity": stock_quantity,
                "sold_quantity": sold_quantity,
                "order_count": len(matching_orders),
                "inventory_value": inventory_value,
                "inventory_cost_value": inventory_cost_value,
                "revenue": revenue,
                "cost": cost,
                "profit": profit,
            }
        ),
    }


def build_orders_report(
    token, *, status_filter="all", from_date=None, to_date=None, include_pending=False, product_id=None
):
    _, order_records = _compute_dataset(
        token, from_date=from_date, to_date=to_date, include_pending=include_pending
    )
    if status_filter != "all":
        order_records = [rec for rec in order_records if rec["status"] == status_filter]
    if product_id is not None:
        order_records = [rec for rec in order_records if product_id in rec["product_ids"]]

    total_sold = sum(o["sold_quantity"] for o in order_records)
    total_revenue = _money(sum((o["revenue"] for o in order_records), ZERO))
    total_product_cost = _money(sum((o["product_cost"] for o in order_records), ZERO))
    total_additional_cost = _money(sum((o["additional_cost"] for o in order_records), ZERO))
    total_cost = _money(total_product_cost + total_additional_cost)
    total_profit = _money(total_revenue - total_cost, allow_negative=True)

    return {
        "filters": _filters_payload(
            from_date, to_date, include_pending, status=status_filter, product_id=product_id
        ),
        "totals": {
            "order_count": len(order_records),
            "completed_order_count": sum(1 for o in order_records if o["status"] == "completed"),
            "pending_order_count": sum(1 for o in order_records if o["status"] == "pending"),
            "cancelled_order_count": sum(1 for o in order_records if o["status"] == "cancelled"),
            "total_sold_quantity": total_sold,
            "total_revenue": _fmt_money(total_revenue),
            "total_product_cost": _fmt_money(total_product_cost),
            "total_additional_cost": _fmt_money(total_additional_cost),
            "total_cost": _fmt_money(total_cost),
            "total_profit": _fmt_money(total_profit),
            "profit_margin_percent": _profit_margin(total_profit, total_revenue),
        },
        "orders": [_serialize_order_record(rec) for rec in order_records],
    }


def build_single_order_report(order_id, token, *, include_pending=False):
    order = get_order(order_id, token, missing_status=404)
    product_costs, order_costs = _load_cost_maps()
    counted_statuses = {"completed", "pending"} if include_pending else {"completed"}
    record = _build_order_record(order, list(order.items), product_costs, order_costs, counted_statuses)
    return {
        "filters": {"include_pending": include_pending},
        "order": _serialize_order_record(record),
    }


# ---------------------------------------------------------------------------
# Persisted Report Snapshots (database: reports.sqlite3)
# ---------------------------------------------------------------------------

def create_report_snapshot(data, user, token):
    from_date = data.get("from_date")
    to_date = data.get("to_date")
    include_pending = data.get("include_pending", False)
    report_type = data.get("report_type", ReportSnapshot.ReportType.FULL)
    title = data.get("title", "Sales & Inventory Report")

    # Fetch all remote data BEFORE opening the SQLite write transaction.
    product_records, order_records = _compute_dataset(
        token, from_date=from_date, to_date=to_date, include_pending=include_pending
    )
    stats = _summarize(product_records, order_records, include_pending)

    created_by = getattr(user, "email", "") or getattr(user, "userid", "")

    with write_transaction():
        snapshot = ReportSnapshot.objects.create(
            title=title,
            report_type=report_type,
            from_date=from_date,
            to_date=to_date,
            include_pending=include_pending,
            total_products=stats["total_products"],
            total_orders=stats["total_orders"],
            completed_orders=stats["completed_orders"],
            pending_orders=stats["pending_orders"],
            cancelled_orders=stats["cancelled_orders"],
            total_stock_quantity=stats["total_stock_quantity"],
            total_sold_quantity=stats["total_sold_quantity"],
            total_inventory_value=stats["total_inventory_value"],
            total_inventory_cost_value=stats["total_inventory_cost_value"],
            total_revenue=stats["total_revenue"],
            total_product_cost=stats["total_product_cost"],
            total_additional_cost=stats["total_additional_cost"],
            total_cost=stats["total_cost"],
            total_profit=stats["total_profit"],
            created_by=created_by,
        )

        if report_type in (ReportSnapshot.ReportType.FULL, ReportSnapshot.ReportType.PRODUCTS):
            ProductReportLine.objects.bulk_create(
                [
                    ProductReportLine(
                        snapshot=snapshot,
                        product_id=rec["product_id"],
                        product_name=rec["product_name"],
                        in_catalog=rec["in_catalog"],
                        unit_price=rec["unit_price"],
                        unit_cost=rec["unit_cost"],
                        cost_configured=rec["cost_configured"],
                        stock_quantity=rec["stock_quantity"],
                        sold_quantity=rec["sold_quantity"],
                        order_count=rec["order_count"],
                        inventory_value=rec["inventory_value"],
                        inventory_cost_value=rec["inventory_cost_value"],
                        revenue=rec["revenue"],
                        cost=rec["cost"],
                        profit=rec["profit"],
                    )
                    for rec in product_records
                ]
            )

        if report_type in (ReportSnapshot.ReportType.FULL, ReportSnapshot.ReportType.ORDERS):
            OrderReportLine.objects.bulk_create(
                [
                    OrderReportLine(
                        snapshot=snapshot,
                        order_id=rec["order_id"],
                        customer_name=rec["customer_name"],
                        customer_email=rec["customer_email"],
                        order_status=rec["status"],
                        order_created_at=rec["created_at"],
                        item_count=rec["item_count"],
                        total_quantity=rec["total_quantity"],
                        sold_quantity=rec["sold_quantity"],
                        order_total_amount=rec["order_total_amount"],
                        revenue=rec["revenue"],
                        product_cost=rec["product_cost"],
                        additional_cost=rec["additional_cost"],
                        total_cost=rec["total_cost"],
                        profit=rec["profit"],
                    )
                    for rec in order_records
                ]
            )

    return ReportSnapshot.objects.prefetch_related("product_lines", "order_lines").get(pk=snapshot.pk)


def delete_report_snapshot(report_id):
    with write_transaction():
        deleted, _ = ReportSnapshot.objects.filter(pk=report_id).delete()
        if deleted == 0:
            raise ReportAPIError(404, "report_not_found", "Report snapshot not found.")
