"""Orders: placing, viewing, cancelling, staff workflow. Owner: Mann.

Placing and cancelling are done by the stored procedures place_order and
cancel_order (all checks, locking and stock changes happen inside the
database). A SIGNAL from them becomes a clean JSON error in main.py.
"""

import json

from fastapi import HTTPException

OPEN_STATUSES = ("placed", "preparing", "ready")
ALL_STATUSES = ("placed", "preparing", "ready", "completed", "cancelled")

# the only forward moves staff can make
NEXT_STATUS = {"placed": "preparing", "preparing": "ready", "ready": "completed"}

_ORDER_SELECT = """
    SELECT o.order_id, o.student_id, u.name AS student_name, u.phone AS student_phone,
           o.canteen_id, o.status, o.payment_status, o.total, o.created_at, o.updated_at
    FROM orders o
    JOIN users u ON u.user_id = o.student_id
"""


def _attach_items(cur, orders):
    """Add an 'items' list to each order (one query for all of them)."""
    if not orders:
        return orders
    ids = [o["order_id"] for o in orders]
    cur.execute(
        f"""SELECT oi.order_id, oi.item_id, m.name, oi.quantity, oi.price_at_order,
                   oi.quantity * oi.price_at_order AS line_total
            FROM order_items oi
            JOIN menu_items m ON m.item_id = oi.item_id
            WHERE oi.order_id IN ({", ".join(["%s"] * len(ids))})
            ORDER BY m.name""",
        ids,
    )
    by_order = {}
    for row in cur.fetchall():
        by_order.setdefault(row.pop("order_id"), []).append(row)
    for o in orders:
        o["items"] = by_order.get(o["order_id"], [])
    return orders


def get_order(conn, order_id):
    with conn.cursor() as cur:
        cur.execute(_ORDER_SELECT + " WHERE o.order_id = %s", (order_id,))
        order = cur.fetchone()
        if order is None:
            raise HTTPException(404, "Order not found")
        return _attach_items(cur, [order])[0]


def _call_procedure(conn, sql, args):
    """Run CALL in a fresh transaction.

    The procedures set READ COMMITTED and start their own transaction,
    which MariaDB refuses while one is open, so we close the read-only
    transaction our earlier SELECTs started.
    """
    conn.commit()
    with conn.cursor() as cur:
        cur.execute(sql, args)


def _default_canteen(cur):
    cur.execute("SELECT canteen_id FROM canteens ORDER BY canteen_id LIMIT 1")
    row = cur.fetchone()
    if row is None:
        raise HTTPException(503, "No canteen is set up yet")
    return row["canteen_id"]


# ---------------------------------------------------------------- students

def place_order(conn, student_id, items):
    """items = [{'item_id': 1, 'quantity': 2}, ...]"""
    with conn.cursor() as cur:
        canteen_id = _default_canteen(cur)
    _call_procedure(conn, "CALL place_order(%s, %s, %s, @new_order_id)",
                    (student_id, canteen_id, json.dumps(items)))
    with conn.cursor() as cur:
        cur.execute("SELECT @new_order_id AS order_id")
        order_id = cur.fetchone()["order_id"]
    return get_order(conn, order_id)


def my_orders(conn, student_id):
    with conn.cursor() as cur:
        cur.execute(_ORDER_SELECT + " WHERE o.student_id = %s ORDER BY o.created_at DESC, o.order_id DESC",
                    (student_id,))
        return _attach_items(cur, cur.fetchall())


def get_order_for(conn, order_id, user):
    """Students see only their own orders; staff and admin see all."""
    order = get_order(conn, order_id)
    if user["role"] == "student" and order["student_id"] != user["user_id"]:
        raise HTTPException(404, "Order not found")  # don't reveal other people's orders
    return order


def cancel(conn, order_id, user):
    """Students may cancel their own order while it is still 'placed'.
    Staff may cancel any order that is not finished."""
    order = get_order_for(conn, order_id, user)
    if user["role"] == "student" and order["status"] in ("preparing", "ready"):
        raise HTTPException(409, "The canteen has started this order, so it can't be cancelled now. "
                                 "Please ask at the counter.")
    _call_procedure(conn, "CALL cancel_order(%s)", (order_id,))
    return get_order(conn, order_id)


# ---------------------------------------------------------------- staff

def list_orders(conn, status=None):
    with conn.cursor() as cur:
        if status:
            if status not in ALL_STATUSES:
                raise HTTPException(400, f"Unknown status '{status}'")
            cur.execute(_ORDER_SELECT + " WHERE o.status = %s ORDER BY o.created_at, o.order_id",
                        (status,))
        else:
            cur.execute(_ORDER_SELECT + " ORDER BY o.created_at DESC, o.order_id DESC")
        return _attach_items(cur, cur.fetchall())


def advance_status(conn, order_id, new_status):
    """Only forward: placed -> preparing -> ready -> completed."""
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM orders WHERE order_id = %s FOR UPDATE", (order_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, "Order not found")
        current = row["status"]
        allowed = NEXT_STATUS.get(current)
        if allowed is None:
            raise HTTPException(409, f"An order that is {current} cannot be moved forward")
        if new_status != allowed:
            raise HTTPException(409, f"Order is {current}; the next status can only be {allowed}")
        cur.execute("UPDATE orders SET status = %s WHERE order_id = %s", (new_status, order_id))
    return get_order(conn, order_id)


def mark_paid(conn, order_id):
    with conn.cursor() as cur:
        cur.execute("SELECT status, payment_status FROM orders WHERE order_id = %s FOR UPDATE",
                    (order_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(404, "Order not found")
        if row["status"] == "cancelled":
            raise HTTPException(409, "A cancelled order cannot be paid")
        if row["payment_status"] == "paid":
            raise HTTPException(409, "This order is already paid")
        cur.execute("UPDATE orders SET payment_status = 'paid' WHERE order_id = %s", (order_id,))
    return get_order(conn, order_id)
