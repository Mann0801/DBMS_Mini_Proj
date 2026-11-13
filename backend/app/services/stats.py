"""MariaDB v2 reporting queries used by staff statistics."""


def _rows(conn, sql, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def daily_sales(conn):
    return _rows(conn, """WITH RECURSIVE days AS (
        SELECT CURDATE() - INTERVAL 6 DAY AS sale_date
        UNION ALL SELECT sale_date + INTERVAL 1 DAY FROM days WHERE sale_date < CURDATE()
    ), sales AS (
        SELECT DATE(created_at) sale_date, SUM(total) total_sales, COUNT(*) order_count
        FROM orders WHERE payment_status='paid' AND status<>'cancelled'
          AND created_at >= CURDATE()-INTERVAL 6 DAY AND created_at < CURDATE()+INTERVAL 1 DAY
        GROUP BY DATE(created_at)
    ) SELECT days.sale_date, COALESCE(sales.total_sales,0) total_sales,
             COALESCE(sales.order_count,0) order_count
      FROM days LEFT JOIN sales USING (sale_date) ORDER BY days.sale_date""")


def top_items(conn):
    return _rows(conn, """WITH units AS (
        SELECT m.item_id,m.name,COALESCE(SUM(CASE WHEN o.payment_status='paid'
          AND o.status<>'cancelled' THEN oi.quantity ELSE 0 END),0) units_sold
        FROM menu_items m LEFT JOIN order_items oi ON oi.item_id=m.item_id
        LEFT JOIN orders o ON o.order_id=oi.order_id GROUP BY m.item_id,m.name
    ) SELECT item_id,name,units_sold,RANK() OVER (ORDER BY units_sold DESC) sales_rank
      FROM units ORDER BY sales_rank,name""")


def running_sales(conn):
    return _rows(conn, """WITH RECURSIVE days AS (
        SELECT CURDATE()-INTERVAL 6 DAY sale_date
        UNION ALL SELECT sale_date+INTERVAL 1 DAY FROM days WHERE sale_date<CURDATE()
    ), daily AS (
        SELECT d.sale_date,COALESCE(SUM(o.total),0) daily_sales FROM days d
        LEFT JOIN orders o ON DATE(o.created_at)=d.sale_date AND o.payment_status='paid'
          AND o.status<>'cancelled' GROUP BY d.sale_date
    ) SELECT sale_date,daily_sales,SUM(daily_sales) OVER (ORDER BY sale_date
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) running_total FROM daily ORDER BY sale_date""")


def category_sales(conn):
    return _rows(conn, """SELECT m.category,COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL
          THEN oi.quantity*oi.price_at_order ELSE 0 END),0) sales_total,
          COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL THEN oi.quantity ELSE 0 END),0) items_sold
        FROM menu_items m
        LEFT JOIN order_items oi ON oi.item_id=m.item_id
        LEFT JOIN orders o ON o.order_id=oi.order_id AND o.payment_status='paid' AND o.status<>'cancelled'
        GROUP BY m.category HAVING COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL
          THEN oi.quantity*oi.price_at_order ELSE 0 END),0)>0
        ORDER BY sales_total DESC,m.category""")


def never_ordered(conn):
    return _rows(conn, """SELECT m.item_id,m.name,m.category,m.price FROM menu_items m
        LEFT JOIN order_items oi ON oi.item_id=m.item_id WHERE oi.item_id IS NULL ORDER BY m.name""")


def above_average_orders(conn):
    return _rows(conn, """SELECT o.order_id,u.name student_name,o.total,o.status,o.payment_status,o.created_at
        FROM orders o JOIN users u ON u.user_id=o.student_id
        WHERE o.status<>'cancelled' AND o.total>(SELECT AVG(total) FROM orders WHERE status<>'cancelled')
        ORDER BY o.total DESC,o.order_id""")


def student_item_set(conn, student_a, student_b, operation):
    operator = "INTERSECT" if operation == "both" else "EXCEPT"
    return _rows(conn, f"""SELECT item_id,name FROM (
        SELECT m.item_id,m.name FROM menu_items m JOIN order_items oi USING(item_id)
          JOIN orders o USING(order_id) WHERE o.student_id=%s AND o.status<>'cancelled'
        {operator}
        SELECT m.item_id,m.name FROM menu_items m JOIN order_items oi USING(item_id)
          JOIN orders o USING(order_id) WHERE o.student_id=%s AND o.status<>'cancelled'
    ) chosen ORDER BY name""", (student_a, student_b))


def top_spenders_by_category(conn):
    return _rows(conn, """WITH spend AS (
        SELECT m.category,u.user_id,u.name student_name,
          SUM(oi.quantity*oi.price_at_order) spent
        FROM orders o JOIN users u ON u.user_id=o.student_id
        JOIN order_items oi ON oi.order_id=o.order_id JOIN menu_items m ON m.item_id=oi.item_id
        WHERE o.payment_status='paid' AND o.status<>'cancelled'
        GROUP BY m.category,u.user_id,u.name
    ) SELECT category,user_id,student_name,spent,
       ROW_NUMBER() OVER (PARTITION BY category ORDER BY spent DESC,student_name) category_rank
       FROM spend ORDER BY category,category_rank""")


def available_view(conn): return _rows(conn, "SELECT * FROM v_available_items ORDER BY category,name")
def sales_report(conn): return _rows(conn, "SELECT * FROM v_sales_report ORDER BY sale_date DESC,category")
def low_stock(conn): return _rows(conn, "SELECT * FROM v_low_stock ORDER BY current_stock,name")
def unpaid_orders(conn): return _rows(conn, "SELECT * FROM v_unpaid_orders ORDER BY created_at DESC,order_id DESC")
