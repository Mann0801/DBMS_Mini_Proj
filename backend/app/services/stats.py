"""Reporting queries for the staff statistics tab."""


def daily_sales(conn):
    with conn.cursor() as cur:
        cur.execute("""WITH RECURSIVE days AS (
                         SELECT CURDATE() - INTERVAL 6 DAY AS sale_date
                         UNION ALL SELECT sale_date + INTERVAL 1 DAY FROM days
                         WHERE sale_date < CURDATE()
                     ), sales AS (
                         SELECT DATE(created_at) AS sale_date, SUM(total) AS total_sales,
                                COUNT(*) AS order_count
                         FROM orders
                         WHERE payment_status = 'paid'
                           AND created_at >= CURDATE() - INTERVAL 6 DAY
                           AND created_at < CURDATE() + INTERVAL 1 DAY
                         GROUP BY DATE(created_at)
                     )
                     SELECT days.sale_date, COALESCE(sales.total_sales, 0) AS total_sales,
                            COALESCE(sales.order_count, 0) AS order_count
                     FROM days LEFT JOIN sales ON sales.sale_date = days.sale_date
                     ORDER BY days.sale_date""")
        return cur.fetchall()


def top_items(conn):
    with conn.cursor() as cur:
        cur.execute("""WITH item_sales AS (
                         SELECT f.id AS food_item_id, f.name,
                                COALESCE(SUM(CASE WHEN o.payment_status = 'paid'
                                                  THEN oi.quantity ELSE 0 END), 0) AS units_sold
                         FROM food_items f
                         LEFT JOIN order_items oi ON oi.food_item_id = f.id
                         LEFT JOIN orders o ON o.id = oi.order_id
                         GROUP BY f.id, f.name
                     )
                     SELECT food_item_id, name, units_sold,
                            RANK() OVER (ORDER BY units_sold DESC) AS sales_rank
                     FROM item_sales ORDER BY sales_rank, name""")
        return cur.fetchall()


def running_sales(conn):
    with conn.cursor() as cur:
        cur.execute("""WITH daily AS (
                         SELECT DATE(created_at) AS sale_date, SUM(total) AS daily_sales
                         FROM orders WHERE payment_status = 'paid'
                         GROUP BY DATE(created_at)
                     )
                     SELECT sale_date, daily_sales,
                            SUM(daily_sales) OVER (ORDER BY sale_date
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
                     FROM daily ORDER BY sale_date""")
        return cur.fetchall()


def category_sales(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT c.id AS category_id, c.name AS category_name,
                            SUM(oi.quantity * oi.price) AS sales_total,
                            SUM(oi.quantity) AS items_sold
                     FROM categories c
                     JOIN food_items f ON f.category_id = c.id
                     JOIN order_items oi ON oi.food_item_id = f.id
                     JOIN orders o ON o.id = oi.order_id
                     WHERE o.payment_status = 'paid'
                     GROUP BY c.id, c.name
                     HAVING SUM(oi.quantity * oi.price) > 0
                     ORDER BY sales_total DESC""")
        return cur.fetchall()


def never_ordered(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT f.id AS food_item_id, f.name, f.price
                     FROM food_items f LEFT JOIN order_items oi ON oi.food_item_id = f.id
                     WHERE oi.food_item_id IS NULL ORDER BY f.name""")
        return cur.fetchall()


def above_average_orders(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT id AS order_id, customer_name, total, created_at
                     FROM orders
                     WHERE total > (SELECT AVG(total) FROM orders)
                     ORDER BY total DESC, id""")
        return cur.fetchall()


def shared_ingredients(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT i.id AS ingredient_id, i.name AS ingredient_name,
                            GROUP_CONCAT(DISTINCT f.name ORDER BY f.name SEPARATOR ', ') AS dishes
                     FROM (
                         SELECT ingredient_id FROM recipes
                         GROUP BY ingredient_id HAVING COUNT(DISTINCT food_item_id) > 1
                         INTERSECT
                         SELECT id FROM ingredients
                     ) shared
                     JOIN ingredients i ON i.id = shared.ingredient_id
                     JOIN recipes r ON r.ingredient_id = i.id
                     JOIN food_items f ON f.id = r.food_item_id
                     GROUP BY i.id, i.name ORDER BY i.name""")
        return cur.fetchall()


def single_dish_ingredients(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT i.id AS ingredient_id, i.name AS ingredient_name,
                            GROUP_CONCAT(DISTINCT f.name ORDER BY f.name SEPARATOR ', ') AS dishes
                     FROM (
                         SELECT ingredient_id FROM recipes
                         EXCEPT
                         SELECT ingredient_id FROM recipes
                         GROUP BY ingredient_id HAVING COUNT(DISTINCT food_item_id) > 1
                     ) exclusive
                     JOIN ingredients i ON i.id = exclusive.ingredient_id
                     JOIN recipes r ON r.ingredient_id = i.id
                     JOIN food_items f ON f.id = r.food_item_id
                     GROUP BY i.id, i.name ORDER BY i.name""")
        return cur.fetchall()


def item_sales(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT f.id AS food_item_id, f.name,
                            COALESCE(SUM(CASE WHEN o.payment_status = 'paid'
                                              THEN oi.quantity * oi.price ELSE 0 END), 0) AS sales_total
                     FROM food_items f
                     LEFT JOIN order_items oi ON oi.food_item_id = f.id
                     LEFT JOIN orders o ON o.id = oi.order_id
                     GROUP BY f.id, f.name ORDER BY sales_total DESC, f.name""")
        return cur.fetchall()


def sales_report(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM v_sales_report ORDER BY sale_date DESC, sales_total DESC")
        return cur.fetchall()


def low_stock(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM v_low_stock ORDER BY name")
        return cur.fetchall()


def unpaid_orders(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM v_unpaid_orders ORDER BY created_at DESC, id DESC")
        return cur.fetchall()


def view_top_items(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM v_top_items ORDER BY units_sold DESC, name")
        return cur.fetchall()
