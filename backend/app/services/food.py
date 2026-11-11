"""Menu and staff food-item operations."""

from fastapi import HTTPException


def menu(conn, query=None, category_id=None):
    """List available menu items, searching short terms with LIKE and others with FULLTEXT."""
    sql = """SELECT f.id, f.name, f.description, f.price, f.category_id,
                     c.name AS category_name, f.is_available
              FROM food_items f JOIN categories c ON c.id = f.category_id
              WHERE f.is_available = TRUE"""
    params = []
    if category_id is not None:
        sql += " AND f.category_id = %s"
        params.append(category_id)
    term = (query or "").strip()
    if term:
        if len(term) <= 3:
            sql += " AND (f.name LIKE %s OR f.description LIKE %s)"
            params.extend((f"%{term}%", f"%{term}%"))
        else:
            sql += " AND MATCH(f.name, f.description) AGAINST (%s IN NATURAL LANGUAGE MODE)"
            params.append(term)
    sql += " ORDER BY c.name, f.name"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def categories(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM categories ORDER BY name")
        return cur.fetchall()


def list_food(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT f.id, f.name, f.description, f.price, f.category_id,
                               c.name AS category_name, f.is_available
                        FROM food_items f JOIN categories c ON c.id = f.category_id
                        ORDER BY c.name, f.name""")
        return cur.fetchall()


def _get(conn, food_id):
    with conn.cursor() as cur:
        cur.execute("""SELECT f.id, f.name, f.description, f.price, f.category_id,
                               c.name AS category_name, f.is_available
                        FROM food_items f JOIN categories c ON c.id = f.category_id
                        WHERE f.id = %s""", (food_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "Food item not found")
    row["is_available"] = bool(row["is_available"])
    return row


def create_food(conn, name, description, price, category_id, is_available=True):
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO food_items (name, description, price, category_id, is_available)
                        VALUES (%s, %s, %s, %s, %s)""",
                    (name, description, price, category_id, is_available))
        food_id = cur.lastrowid
    return _get(conn, food_id)


def update_food(conn, food_id, name, description, price, category_id, is_available):
    with conn.cursor() as cur:
        cur.execute("""UPDATE food_items
                        SET name = %s, description = %s, price = %s,
                            category_id = %s, is_available = %s
                        WHERE id = %s""",
                    (name, description, price, category_id, is_available, food_id))
        if cur.rowcount == 0:
            cur.execute("SELECT id FROM food_items WHERE id = %s", (food_id,))
            if cur.fetchone() is None:
                raise HTTPException(404, "Food item not found")
    return _get(conn, food_id)


def delete_food(conn, food_id):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM food_items WHERE id = %s FOR UPDATE", (food_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, "Food item not found")
        cur.execute("SELECT 1 FROM order_items WHERE food_item_id = %s LIMIT 1", (food_id,))
        has_orders = cur.fetchone() is not None
        if has_orders:
            cur.execute("UPDATE food_items SET is_available = FALSE WHERE id = %s", (food_id,))
        else:
            cur.execute("DELETE FROM food_items WHERE id = %s", (food_id,))
    return {"id": food_id, "deleted": not has_orders, "is_available": False if has_orders else None}
