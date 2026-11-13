"""Stock: list, restock / adjust, low-stock alerts, history. Owner: Mann.

Every stock change goes through UPDATE menu_items, so the trigger
trg_menu_stock_log writes it to inventory_transactions. We only set
@txn_reason / @txn_order_id first so the log says why.
"""

from fastapi import HTTPException

# Correlated subquery: for EACH menu item (outer row m), the inner query
# adds up how many were ordered in the last 7 days.
_STOCK_SELECT = """
    SELECT m.item_id, m.name, m.category, m.current_stock, m.low_stock_threshold, m.status,
           (m.current_stock <= m.low_stock_threshold) AS is_low,
           (SELECT COALESCE(SUM(oi.quantity), 0)
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE oi.item_id = m.item_id                      -- outer reference
              AND o.status <> 'cancelled'
              AND o.created_at >= NOW() - INTERVAL 7 DAY) AS sold_last_7_days
    FROM menu_items m
"""


def _fix(rows):
    for r in rows:
        r["is_low"] = bool(r["is_low"])
        r["sold_last_7_days"] = int(r["sold_last_7_days"])
    return rows


def get_item_stock(conn, item_id):
    with conn.cursor() as cur:
        cur.execute(_STOCK_SELECT + " WHERE m.item_id = %s", (item_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "Menu item not found")
    return _fix([row])[0]


def list_stock(conn):
    with conn.cursor() as cur:
        cur.execute(_STOCK_SELECT + " WHERE m.status <> 'delisted' ORDER BY m.category, m.name")
        return _fix(cur.fetchall())


def low_stock(conn):
    with conn.cursor() as cur:
        cur.execute(_STOCK_SELECT + """ WHERE m.status <> 'delisted'
                                        AND m.current_stock <= m.low_stock_threshold
                                        ORDER BY m.current_stock, m.name""")
        return _fix(cur.fetchall())


def change_stock(conn, item_id, amount, reason):
    """amount > 0 for restock; < 0 for wastage / correction."""
    with conn.cursor() as cur:
        cur.execute("SELECT name, current_stock, status FROM menu_items WHERE item_id = %s FOR UPDATE",
                    (item_id,))
        item = cur.fetchone()
        if item is None:
            raise HTTPException(404, "Menu item not found")
        if item["status"] == "delisted":
            raise HTTPException(409, f"{item['name']} is delisted; put it back on the menu first")
        if item["current_stock"] + amount < 0:
            raise HTTPException(409, f"Only {item['current_stock']} {item['name']} in stock; "
                                     f"you can't remove {abs(amount)}")
        cur.execute("SET @txn_reason = %s, @txn_order_id = NULL", (reason,))
        cur.execute("UPDATE menu_items SET current_stock = current_stock + %s WHERE item_id = %s",
                    (amount, item_id))
        cur.execute("SET @txn_reason = NULL")
    return get_item_stock(conn, item_id)


def history(conn, item_id, limit=50):
    get_item_stock(conn, item_id)  # 404 if missing
    with conn.cursor() as cur:
        cur.execute(
            """SELECT txn_id, order_id, change_amount, reason, created_at
               FROM inventory_transactions
               WHERE item_id = %s
               ORDER BY created_at DESC, txn_id DESC
               LIMIT %s""",
            (item_id, limit),
        )
        return cur.fetchall()
