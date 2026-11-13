-- CampusEats v2 viva query sheet. Run after schema.sql and seed.sql.

-- DML examples (the temporary row is inserted, edited, and removed).
INSERT INTO menu_items (canteen_id,name,description,category,price,current_stock,low_stock_threshold,status)
VALUES (1,'Demo Special','Temporary viva demonstration item','Snacks',25.00,8,2,'available');
SET @demo_item_id = LAST_INSERT_ID();
UPDATE menu_items SET price=28.00, description='Edited during the DML demonstration'
WHERE item_id=@demo_item_id;
DELETE FROM menu_items WHERE item_id=@demo_item_id;

-- 1. Daily paid sales for the last seven calendar days, including zero days (recursive CTE).
WITH RECURSIVE days AS (
  SELECT CURDATE()-INTERVAL 6 DAY AS sale_date
  UNION ALL SELECT sale_date+INTERVAL 1 DAY FROM days WHERE sale_date<CURDATE()
), sales AS (
  SELECT DATE(created_at) sale_date,SUM(total) total_sales,COUNT(*) order_count
  FROM orders WHERE payment_status='paid' AND status<>'cancelled'
    AND created_at>=CURDATE()-INTERVAL 6 DAY AND created_at<CURDATE()+INTERVAL 1 DAY
  GROUP BY DATE(created_at)
)
SELECT days.sale_date,COALESCE(sales.total_sales,0) total_sales,COALESCE(sales.order_count,0) order_count
FROM days LEFT JOIN sales USING(sale_date) ORDER BY days.sale_date;

-- 2. Best-selling items with rank.
WITH units AS (
  SELECT m.item_id,m.name,COALESCE(SUM(CASE WHEN o.payment_status='paid' AND o.status<>'cancelled'
    THEN oi.quantity ELSE 0 END),0) units_sold
  FROM menu_items m LEFT JOIN order_items oi ON oi.item_id=m.item_id
  LEFT JOIN orders o ON o.order_id=oi.order_id GROUP BY m.item_id,m.name
)
SELECT item_id,name,units_sold,RANK() OVER(ORDER BY units_sold DESC) sales_rank
FROM units ORDER BY sales_rank,name;

-- 3. Running paid sales total (window SUM).
WITH daily AS (
  SELECT DATE(created_at) sale_date,SUM(total) daily_sales FROM orders
  WHERE payment_status='paid' AND status<>'cancelled' GROUP BY DATE(created_at)
)
SELECT sale_date,daily_sales,SUM(daily_sales) OVER(ORDER BY sale_date
  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) running_total FROM daily ORDER BY sale_date;

-- 4. Sales grouped by category and filtered with HAVING.
SELECT m.category,COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL
  THEN oi.quantity*oi.price_at_order ELSE 0 END),0) sales_total,
  COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL THEN oi.quantity ELSE 0 END),0) items_sold
FROM menu_items m LEFT JOIN order_items oi ON oi.item_id=m.item_id
LEFT JOIN orders o ON o.order_id=oi.order_id AND o.payment_status='paid' AND o.status<>'cancelled'
GROUP BY m.category HAVING COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL
  THEN oi.quantity*oi.price_at_order ELSE 0 END),0)>=0
ORDER BY sales_total DESC,m.category;

-- 5. Menu items never ordered (LEFT JOIN / IS NULL).
SELECT m.item_id,m.name,m.category FROM menu_items m
LEFT JOIN order_items oi ON oi.item_id=m.item_id WHERE oi.item_id IS NULL ORDER BY m.name;

-- 6. Orders above the average; cancelled orders are excluded from both levels.
SELECT o.order_id,u.name student_name,o.total,o.status FROM orders o
JOIN users u ON u.user_id=o.student_id
WHERE o.status<>'cancelled' AND o.total>(SELECT AVG(total) FROM orders WHERE status<>'cancelled')
ORDER BY o.total DESC;

-- 7. Items ordered by both chosen students (edit IDs as needed).
SET @student_a=4, @student_b=5;
SELECT m.item_id,m.name FROM menu_items m JOIN order_items oi USING(item_id)
JOIN orders o USING(order_id) WHERE o.student_id=@student_a AND o.status<>'cancelled'
INTERSECT
SELECT m.item_id,m.name FROM menu_items m JOIN order_items oi USING(item_id)
JOIN orders o USING(order_id) WHERE o.student_id=@student_b AND o.status<>'cancelled';

-- 8. Items A ordered but B did not (EXCEPT).
SELECT m.item_id,m.name FROM menu_items m JOIN order_items oi USING(item_id)
JOIN orders o USING(order_id) WHERE o.student_id=@student_a AND o.status<>'cancelled'
EXCEPT
SELECT m.item_id,m.name FROM menu_items m JOIN order_items oi USING(item_id)
JOIN orders o USING(order_id) WHERE o.student_id=@student_b AND o.status<>'cancelled';

-- 9. Highest spending students in each category (ROW_NUMBER partitioned by category).
WITH spend AS (
  SELECT m.category,u.user_id,u.name student_name,SUM(oi.quantity*oi.price_at_order) spent
  FROM orders o JOIN users u ON u.user_id=o.student_id JOIN order_items oi ON oi.order_id=o.order_id
  JOIN menu_items m ON m.item_id=oi.item_id
  WHERE o.payment_status='paid' AND o.status<>'cancelled'
  GROUP BY m.category,u.user_id,u.name
)
SELECT category,user_id,student_name,spent,
  ROW_NUMBER() OVER(PARTITION BY category ORDER BY spent DESC,student_name) category_rank
FROM spend ORDER BY category,category_rank;

-- 10-13. Manoj's four report views.
SELECT * FROM v_available_items ORDER BY category,name;
SELECT * FROM v_sales_report ORDER BY sale_date DESC,category;
SELECT * FROM v_low_stock ORDER BY current_stock,name;
SELECT * FROM v_unpaid_orders ORDER BY created_at DESC,order_id DESC;
