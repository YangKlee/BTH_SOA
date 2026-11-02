"""Order mutations: remote checks first, then a short serialized SQLite write."""

from contextlib import contextmanager
from decimal import Decimal

from django.db import IntegrityError, OperationalError, transaction
from django.utils import timezone

from .clients.product import ensure_stock, get_product
from .errors import OrderAPIError
from .models import Order, OrderItem


MAX_AMOUNT = Decimal("99999999.99")
CENT = Decimal("0.01")


@contextmanager
def write_transaction():
    # SQLite's configured IMMEDIATE transaction acquires its write lock before
    # reading mutable state. Never issue HTTP from within this block.
    try:
        with transaction.atomic():
            yield
    except OperationalError as exc:
        if "locked" in str(exc).lower() or "busy" in str(exc).lower():
            raise OrderAPIError(
                503, "database_busy", "Order database is busy. Please try again."
            ) from exc
        raise
    except IntegrityError as exc:
        raise OrderAPIError(
            409, "data_conflict", "The order changed or violates a data constraint."
        ) from exc


def _order(order_id):
    order = Order.objects.filter(pk=order_id).first()
    if order is None:
        raise OrderAPIError(404, "order_not_found", "Order not found.")
    return order


def _item(item_id):
    item = OrderItem.objects.filter(pk=item_id).first()
    if item is None:
        raise OrderAPIError(404, "item_not_found", "Order item not found.")
    return item


def _pending(order):
    if order.status != "pending":
        raise OrderAPIError(
            409, "order_not_pending", "Only pending orders can have their items changed."
        )


def _money(value):
    if not value.is_finite() or value < 0 or value > MAX_AMOUNT:
        raise OrderAPIError(
            400, "amount_overflow", "An item or order total exceeds DECIMAL(10,2)."
        )
    return value.quantize(CENT)


def _recalculate(order):
    # Sum Decimal objects in Python, avoiding SQLite floating-point SUM.
    total = _money(sum(order.items.values_list("total_price", flat=True), Decimal("0.00")))
    order.total_amount = total
    order.updated_at = timezone.now()
    order.save(update_fields=["total_amount", "updated_at"])


def create_order(data, token):
    lines = data["items"]
    if not lines:
        raise OrderAPIError(400, "empty_order", "An order requires at least one item.")
    if len({line["product_id"] for line in lines}) != len(lines):
        raise OrderAPIError(400, "duplicate_product", "A product can appear only once per order.")

    snapshots = []
    total = Decimal("0.00")
    for line in lines:
        product = get_product(line["product_id"], token)
        ensure_stock(product, line["quantity"])
        line_total = _money(product.price * line["quantity"])
        total = _money(total + line_total)
        snapshots.append((product, line["quantity"], line_total))

    with write_transaction():
        order = Order.objects.create(
            customer_name=data["customer_name"],
            customer_email=data["customer_email"],
            status="pending",
            total_amount=total,
        )
        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product_id=product.id,
                product_name=product.name,
                quantity=quantity,
                unit_price=product.price,
                total_price=line_total,
            )
            for product, quantity, line_total in snapshots
        ])
    return order


def add_item(data, token):
    order = _order(data["order_id"])
    _pending(order)
    if order.items.filter(product_id=data["product_id"]).exists():
        raise OrderAPIError(409, "duplicate_product", "This product is already in the order.")
    product = get_product(data["product_id"], token)
    ensure_stock(product, data["quantity"])
    line_total = _money(product.price * data["quantity"])

    with write_transaction():
        order = _order(data["order_id"])
        _pending(order)
        if order.items.filter(product_id=product.id).exists():
            raise OrderAPIError(409, "duplicate_product", "This product is already in the order.")
        item = OrderItem.objects.create(
            order=order,
            product_id=product.id,
            product_name=product.name,
            quantity=data["quantity"],
            unit_price=product.price,
            total_price=line_total,
        )
        _recalculate(order)
    return item


def update_item(item_id, quantity, token):
    item = _item(item_id)
    _pending(_order(item.order_id))
    product = get_product(item.product_id, token)
    ensure_stock(product, quantity)

    with write_transaction():
        item = _item(item_id)
        order = _order(item.order_id)
        _pending(order)
        item.quantity = quantity
        item.total_price = _money(item.unit_price * quantity)
        item.save(update_fields=["quantity", "total_price"])
        _recalculate(order)
    return item


def delete_item(item_id):
    with write_transaction():
        item = _item(item_id)
        order = _order(item.order_id)
        _pending(order)
        if order.items.count() <= 1:
            raise OrderAPIError(409, "last_item", "The final item cannot be deleted; delete the order instead.")
        item.delete()
        _recalculate(order)


def _signature(items):
    return [(item.id, item.product_id, item.quantity) for item in items]


def change_order_status(order_id, status, token):
    initial = _order(order_id)
    if status not in {"pending", "completed", "cancelled"}:
        raise OrderAPIError(400, "invalid_status", "Invalid order status.")
    checked_signature = None
    if initial.status != status:
        _pending(initial)
        if status == "completed":
            items = list(initial.items.order_by("id"))
            checked_signature = _signature(items)
            for item in items:
                ensure_stock(get_product(item.product_id, token), item.quantity)

    with write_transaction():
        order = _order(order_id)
        if order.status == status:
            return order
        _pending(order)
        # A same-status request can become a transition while waiting for the
        # lock. It must not bypass the checks needed for that transition.
        if status == "pending":
            raise OrderAPIError(409, "invalid_transition", "An order cannot return to pending.")
        if status == "completed":
            current_signature = _signature(order.items.order_by("id"))
            if checked_signature is None or checked_signature != current_signature:
                raise OrderAPIError(409, "order_changed", "Order items changed during stock checks; please retry.")
        order.status = status
        order.updated_at = timezone.now()
        order.save(update_fields=["status", "updated_at"])
    return order


def delete_order(order_id):
    with write_transaction():
        _order(order_id).delete()
