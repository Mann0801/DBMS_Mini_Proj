"""Order logic: placing, tracking and the staff workflow.

Every function takes an open connection (from database.get_db) and uses
parameterized queries only.
"""

from fastapi import HTTPException

MAX_PER_ITEM = 10
MAX_OPEN_ORDERS_PER_PHONE = 3
OPEN_STATUSES = ("placed", "accepted", "preparing", "ready")
ALL_STATUSES = ("placed", "accepted", "preparing", "ready", "collected", "rejected")

# The only forward moves staff can make with the status button.
NEXT_STATUS = {
    "accepted": "preparing",
    "preparing": "ready",
    "ready": "collected",
}


# ---------------------------------------------------------------- helpers

def _attach_items(cur, orders):
    """Add an 'items' list to each order dict (one query for all orders)."""
    if not orders:
        return orders
    ids = [o["id"] for o in orders]
    placeholders = ", ".join(["%s"] * len(ids))
    cur.execute(
        f"""SELECT oi.order_id, oi.food_item_id, f.name, oi.quantity, oi.price,
                   oi.quantity * oi.price AS line_total
            FROM order_items oi
            JOIN food_items f ON f.id = oi.food_item_id
            WHERE oi.order_id IN ({placeholders})
            ORDER BY f.name""",
        ids,
    )
    by_order = {}
    for row in cur.fetchall():
        by_order.setdefault(row.pop("order_id"), []).append(row)
    for o in orders:
        o["items"] = by_order.get(o["id"], [])
    return orders


def _get_order_row(cur, order_id, lock=False):
    sql = "SELECT * FROM orders WHERE id = %s"
    if lock:
        sql += " FOR UPDATE"
    cur.execute(sql, (order_id,))
    order = cur.fetchone()
    if order is None:
        raise HTTPException(404, "Order not found")
    return order


def get_order_by_id(conn, order_id):
    with conn.cursor() as cur:
        order = _get_order_row(cur, order_id)
        return _attach_items(cur, [order])[0]


# ---------------------------------------------------------------- students

def place_order(conn, name, phone, items):
    """items = [{'food_item_id': int, 'quantity': int}, ...]"""
    # merge duplicate lines for the same item
    wanted = {}
    for it in items:
        wanted[it["food_item_id"]] = wanted.get(it["food_item_id"], 0) + it["quantity"]
    for qty in wanted.values():
        if qty > MAX_PER_ITEM:
            raise HTTPException(400, f"You can order at most {MAX_PER_ITEM} of any one item")

    with conn.cursor() as cur:
        # limit open orders per phone
        cur.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE customer_phone = %s AND status IN %s",
            (phone, OPEN_STATUSES),
        )
        if cur.fetchone()["n"] >= MAX_OPEN_ORDERS_PER_PHONE:
            raise HTTPException(
                400,
                f"This phone number already has {MAX_OPEN_ORDERS_PER_PHONE} open orders. "
                "Please collect them first.",
            )

        # prices come from the database, never from the browser
        ids = list(wanted)
        placeholders = ", ".join(["%s"] * len(ids))
        cur.execute(
            f"SELECT id, name, price, is_available FROM food_items WHERE id IN ({placeholders})",
            ids,
        )
        foods = {row["id"]: row for row in cur.fetchall()}

        for fid in ids:
            if fid not in foods:
                raise HTTPException(400, f"Food item {fid} does not exist")
            if not foods[fid]["is_available"]:
                raise HTTPException(400, f"{foods[fid]['name']} is not available right now")

        total = sum(foods[fid]["price"] * qty for fid, qty in wanted.items())

        cur.execute(
            "INSERT INTO orders (customer_name, customer_phone, total) VALUES (%s, %s, %s)",
            (name, phone, total),
        )
        order_id = cur.lastrowid

        cur.executemany(
            "INSERT INTO order_items (order_id, food_item_id, quantity, price) "
            "VALUES (%s, %s, %s, %s)",
            [(order_id, fid, qty, foods[fid]["price"]) for fid, qty in wanted.items()],
        )

    return get_order_by_id(conn, order_id)


def track_order(conn, order_id, phone):
    """Only return the order if the phone number matches."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM orders WHERE id = %s AND customer_phone = %s",
            (order_id, phone),
        )
        order = cur.fetchone()
        if order is None:
            # same message whether the id or the phone is wrong
            raise HTTPException(404, "No order found with that number and phone")
        return _attach_items(cur, [order])[0]


def orders_for_phone(conn, phone):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM orders WHERE customer_phone = %s ORDER BY created_at DESC, id DESC",
            (phone,),
        )
        return _attach_items(cur, cur.fetchall())


# ---------------------------------------------------------------- staff

def list_orders(conn, status=None):
    with conn.cursor() as cur:
        if status:
            if status not in ALL_STATUSES:
                raise HTTPException(400, f"Unknown status '{status}'")
            cur.execute(
                "SELECT * FROM orders WHERE status = %s ORDER BY created_at, id",
                (status,),
            )
        else:
            cur.execute("SELECT * FROM orders ORDER BY created_at DESC, id DESC")
        return _attach_items(cur, cur.fetchall())


def accept_order(conn, order_id):
    # all checks, locking and stock deduction happen inside the procedure;
    # a SIGNAL from it becomes a clean error message in main.py
    with conn.cursor() as cur:
        cur.execute("CALL accept_order(%s)", (order_id,))
    return get_order_by_id(conn, order_id)


def cancel_order(conn, order_id):
    with conn.cursor() as cur:
        cur.execute("CALL cancel_order(%s)", (order_id,))
    return get_order_by_id(conn, order_id)


def reject_order(conn, order_id):
    """Reject a new order. Stock was never taken, so nothing to restore."""
    with conn.cursor() as cur:
        order = _get_order_row(cur, order_id, lock=True)
        if order["status"] != "placed":
            raise HTTPException(
                409,
                f"Only placed orders can be rejected (this order is {order['status']}). "
                "Use cancel for accepted orders.",
            )
        cur.execute("UPDATE orders SET status = 'rejected' WHERE id = %s", (order_id,))
    return get_order_by_id(conn, order_id)


def advance_status(conn, order_id, new_status):
    """Only forward moves: accepted -> preparing -> ready -> collected."""
    with conn.cursor() as cur:
        order = _get_order_row(cur, order_id, lock=True)
        current = order["status"]
        allowed = NEXT_STATUS.get(current)
        if allowed is None:
            raise HTTPException(409, f"An order that is {current} cannot be moved forward")
        if new_status != allowed:
            raise HTTPException(
                409, f"Order is {current}; the next status can only be {allowed}"
            )
        cur.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
    return get_order_by_id(conn, order_id)


def mark_paid(conn, order_id):
    with conn.cursor() as cur:
        order = _get_order_row(cur, order_id, lock=True)
        if order["status"] == "rejected":
            raise HTTPException(409, "A rejected order cannot be paid")
        if order["status"] == "placed":
            raise HTTPException(409, "Accept the order before marking it paid")
        if order["payment_status"] == "paid":
            raise HTTPException(409, "This order is already paid")
        cur.execute("UPDATE orders SET payment_status = 'paid' WHERE id = %s", (order_id,))
    return get_order_by_id(conn, order_id)
