"""Parameterized menu operations for the v2 menu_items schema."""

from fastapi import HTTPException
import re


def menu(conn, query=None, category=None):
    sql = """SELECT m.item_id, m.canteen_id, c.name AS canteen_name, c.location,
                    m.name, m.description, m.category, m.price, m.current_stock,
                    m.low_stock_threshold, m.status
             FROM menu_items AS m JOIN canteens AS c ON c.canteen_id=m.canteen_id
             WHERE m.status='available'"""
    params = []
    if category:
        sql += " AND m.category = %s"
        params.append(category)
    words = [word for word in (re.sub(r"[^\w]", "", part) for part in (query or "").split()) if word]
    if words:
        for word in words:
            if len(word) <= 3:
                sql += " AND (m.name LIKE %s OR m.description LIKE %s OR m.category LIKE %s)"
                params.extend([f"%{word}%"] * 3)
            else:
                sql += " AND MATCH(m.name, m.description, m.category) AGAINST (%s IN BOOLEAN MODE)"
                params.append(f"+{word}*")
    sql += " ORDER BY m.category, m.name"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def categories(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT category FROM menu_items ORDER BY category")
        return [row["category"] for row in cur.fetchall()]


def list_food(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT item_id, canteen_id, name, description, category, price,
                               current_stock, low_stock_threshold, status, created_at
                        FROM menu_items ORDER BY category, name""")
        return cur.fetchall()


def _get(conn, item_id):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM menu_items WHERE item_id=%s", (item_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "Menu item not found")
    return row


def create_food(conn, name, description, category, price, current_stock, low_stock_threshold):
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO menu_items
            (canteen_id,name,description,category,price,current_stock,low_stock_threshold,status)
            VALUES (1,%s,%s,%s,%s,%s,%s,%s)""",
            (name, description, category, price, current_stock, low_stock_threshold,
             "sold_out" if current_stock == 0 else "available"))
        item_id = cur.lastrowid
    return _get(conn, item_id)


def update_food(conn, item_id, name, description, category, price, status):
    with conn.cursor() as cur:
        cur.execute("""UPDATE menu_items SET name=%s, description=%s, category=%s,
                            price=%s, status=%s WHERE item_id=%s""",
                    (name, description, category, price, status, item_id))
        if cur.rowcount == 0:
            cur.execute("SELECT item_id FROM menu_items WHERE item_id=%s", (item_id,))
            if cur.fetchone() is None:
                raise HTTPException(404, "Menu item not found")
    return _get(conn, item_id)


def delete_food(conn, item_id):
    with conn.cursor() as cur:
        cur.execute("SELECT item_id FROM menu_items WHERE item_id=%s FOR UPDATE", (item_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, "Menu item not found")
        cur.execute("SELECT 1 FROM order_items WHERE item_id=%s LIMIT 1", (item_id,))
        has_orders = cur.fetchone() is not None
        if has_orders:
            cur.execute("UPDATE menu_items SET status='delisted' WHERE item_id=%s", (item_id,))
        else:
            cur.execute("DELETE FROM menu_items WHERE item_id=%s", (item_id,))
    return {"item_id": item_id, "deleted": not has_orders, "status": "delisted" if has_orders else None}
