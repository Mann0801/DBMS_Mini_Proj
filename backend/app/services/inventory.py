"""Ingredient stock: list, add, restock, low-stock alerts.

Stock changes are logged by the database trigger; we only set the session
variables @txn_reason / @txn_order_id before updating.
"""

from fastapi import HTTPException

_SELECT = """
    SELECT id, name, unit, stock, low_stock_threshold,
           (stock <= low_stock_threshold) AS is_low
    FROM ingredients
"""


def _fix_bool(rows):
    for r in rows:
        r["is_low"] = bool(r["is_low"])
    return rows


def get_ingredient(conn, ingredient_id):
    with conn.cursor() as cur:
        cur.execute(_SELECT + " WHERE id = %s", (ingredient_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "Ingredient not found")
    return _fix_bool([row])[0]


def list_ingredients(conn):
    with conn.cursor() as cur:
        cur.execute(_SELECT + " ORDER BY name")
        return _fix_bool(cur.fetchall())


def low_stock(conn):
    with conn.cursor() as cur:
        cur.execute(_SELECT + " WHERE stock <= low_stock_threshold ORDER BY stock / NULLIF(low_stock_threshold, 0)")
        return _fix_bool(cur.fetchall())


def add_ingredient(conn, name, unit, stock, low_stock_threshold):
    # a duplicate name raises IntegrityError 1062 -> clean 409 in main.py
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ingredients (name, unit, stock, low_stock_threshold) "
            "VALUES (%s, %s, %s, %s)",
            (name, unit, stock, low_stock_threshold),
        )
        new_id = cur.lastrowid
    return get_ingredient(conn, new_id)


def add_stock(conn, ingredient_id, amount):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM ingredients WHERE id = %s FOR UPDATE", (ingredient_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, "Ingredient not found")
        # tell the trigger why stock is changing
        cur.execute("SET @txn_reason = 'restock', @txn_order_id = NULL")
        cur.execute(
            "UPDATE ingredients SET stock = stock + %s WHERE id = %s",
            (amount, ingredient_id),
        )
        cur.execute("SET @txn_reason = NULL")
    return get_ingredient(conn, ingredient_id)


def dish_availability(conn):
    """How many portions of each dish the current stock can make.

    - portions_available(f.id) is a stored function
    - missing_ingredients is a CORRELATED subquery: it runs once per dish,
      using the outer row's f.id
    - can_make uses a correlated NOT EXISTS
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT f.id AS food_item_id,
                   f.name,
                   COALESCE(portions_available(f.id), 0) AS portions_left,
                   (SELECT GROUP_CONCAT(i.name ORDER BY i.name SEPARATOR ', ')
                    FROM recipes r
                    JOIN ingredients i ON i.id = r.ingredient_id
                    WHERE r.food_item_id = f.id          -- outer reference
                      AND i.stock < r.quantity_needed) AS missing_ingredients,
                   NOT EXISTS (SELECT 1
                               FROM recipes r
                               JOIN ingredients i ON i.id = r.ingredient_id
                               WHERE r.food_item_id = f.id
                                 AND i.stock < r.quantity_needed) AS can_make
            FROM food_items f
            WHERE f.is_available = TRUE
            ORDER BY portions_left, f.name
        """)
        rows = cur.fetchall()
    for r in rows:
        r["can_make"] = bool(r["can_make"])
    return rows


def transactions(conn, ingredient_id, limit=50):
    """Recent stock history for one ingredient."""
    get_ingredient(conn, ingredient_id)  # 404 if it doesn't exist
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, order_id, change_amount, reason, created_at
               FROM inventory_transactions
               WHERE ingredient_id = %s
               ORDER BY created_at DESC, id DESC
               LIMIT %s""",
            (ingredient_id, limit),
        )
        return cur.fetchall()
