-- =====================================================================
-- CampusEats v2 schema (MariaDB 11)
-- Load with:  mariadb -u campuseats -p campuseats < database/schema.sql
-- Re-running this file drops and recreates everything.
--
-- Sections:
--   MANN  : users, orders, order_items, inventory_transactions,
--           triggers, place_order, cancel_order, order_total()
--   MANOJ : canteens, menu_items, FULLTEXT index, views
-- Only edit your own section.
-- =====================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ---------- drop everything (safe to re-run) ----------
DROP VIEW IF EXISTS v_available_items;
DROP VIEW IF EXISTS v_sales_report;
DROP VIEW IF EXISTS v_low_stock;
DROP VIEW IF EXISTS v_unpaid_orders;
DROP VIEW IF EXISTS v_top_items;

DROP PROCEDURE IF EXISTS place_order;
DROP PROCEDURE IF EXISTS cancel_order;
DROP PROCEDURE IF EXISTS accept_order;
DROP FUNCTION IF EXISTS order_total;
DROP FUNCTION IF EXISTS portions_available;
DROP TRIGGER IF EXISTS trg_menu_stock_status;
DROP TRIGGER IF EXISTS trg_menu_stock_log;
DROP TRIGGER IF EXISTS trg_ingredients_stock_log;

DROP TABLE IF EXISTS inventory_transactions;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS menu_items;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS canteens;
-- tables from the old (v1) design
DROP TABLE IF EXISTS recipes;
DROP TABLE IF EXISTS ingredients;
DROP TABLE IF EXISTS food_items;
DROP TABLE IF EXISTS categories;

SET FOREIGN_KEY_CHECKS = 1;


-- =====================================================================
-- MANOJ: canteens and menu
-- Manoj owns these tables, the FULLTEXT index, and the report views.
-- Mann's code uses every column below, so keep the names.
-- =====================================================================

CREATE TABLE canteens (
    canteen_id INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100) NOT NULL UNIQUE,
    location   VARCHAR(150) NOT NULL
) ENGINE = InnoDB;

CREATE TABLE menu_items (
    item_id             INT AUTO_INCREMENT PRIMARY KEY,
    canteen_id          INT           NOT NULL,
    name                VARCHAR(100)  NOT NULL,
    description         VARCHAR(255),
    category            VARCHAR(50)   NOT NULL,
    price               DECIMAL(8, 2) NOT NULL,
    current_stock       INT           NOT NULL DEFAULT 0,
    low_stock_threshold INT           NOT NULL DEFAULT 5,
    status              VARCHAR(20)   NOT NULL DEFAULT 'available',
    created_at          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_menu_name   UNIQUE (canteen_id, name),
    CONSTRAINT chk_menu_price CHECK (price > 0),
    CONSTRAINT chk_menu_stock CHECK (current_stock >= 0),
    CONSTRAINT chk_menu_low   CHECK (low_stock_threshold >= 0),
    CONSTRAINT chk_menu_status CHECK (status IN ('available', 'sold_out', 'delisted')),
    CONSTRAINT fk_menu_canteen FOREIGN KEY (canteen_id)
        REFERENCES canteens (canteen_id) ON DELETE CASCADE
) ENGINE = InnoDB;

CREATE INDEX idx_menu_canteen ON menu_items (canteen_id);
CREATE INDEX idx_menu_status  ON menu_items (status);
CREATE FULLTEXT INDEX ft_menu_search ON menu_items (name, description, category);


-- =====================================================================
-- MANN: accounts, orders, stock history
-- =====================================================================

CREATE TABLE users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,          -- never the real password
    role          VARCHAR(20)  NOT NULL DEFAULT 'student',
    phone         CHAR(10),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_user_role  CHECK (role IN ('admin', 'staff', 'student')),
    CONSTRAINT chk_user_email CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT chk_user_name  CHECK (CHAR_LENGTH(TRIM(name)) > 0),
    -- NULL allowed; if given, a 10-digit Indian mobile number
    CONSTRAINT chk_user_phone CHECK (phone IS NULL OR phone REGEXP '^[6-9][0-9]{9}$')
) ENGINE = InnoDB;

CREATE TABLE orders (
    order_id       INT AUTO_INCREMENT PRIMARY KEY,
    student_id     INT            NOT NULL,
    canteen_id     INT            NOT NULL,
    status         VARCHAR(20)    NOT NULL DEFAULT 'placed',
    payment_status VARCHAR(10)    NOT NULL DEFAULT 'unpaid',
    total          DECIMAL(10, 2) NOT NULL DEFAULT 0,
    created_at     TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_order_status CHECK (status IN
        ('placed', 'preparing', 'ready', 'completed', 'cancelled')),
    CONSTRAINT chk_order_payment CHECK (payment_status IN ('unpaid', 'paid')),
    CONSTRAINT chk_order_total CHECK (total >= 0),
    CONSTRAINT fk_order_student FOREIGN KEY (student_id)
        REFERENCES users (user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_order_canteen FOREIGN KEY (canteen_id)
        REFERENCES canteens (canteen_id) ON DELETE RESTRICT
) ENGINE = InnoDB;

CREATE INDEX idx_orders_student ON orders (student_id);
CREATE INDEX idx_orders_status  ON orders (status);

-- price_at_order = snapshot of menu_items.price when the order was placed
CREATE TABLE order_items (
    order_id       INT           NOT NULL,
    item_id        INT           NOT NULL,
    quantity       INT           NOT NULL,
    price_at_order DECIMAL(8, 2) NOT NULL,
    PRIMARY KEY (order_id, item_id),
    CONSTRAINT chk_oi_qty   CHECK (quantity BETWEEN 1 AND 10),
    CONSTRAINT chk_oi_price CHECK (price_at_order >= 0),
    CONSTRAINT fk_oi_order FOREIGN KEY (order_id)
        REFERENCES orders (order_id) ON DELETE CASCADE,
    -- no cascade: an item with past orders cannot be deleted
    CONSTRAINT fk_oi_item FOREIGN KEY (item_id)
        REFERENCES menu_items (item_id) ON DELETE RESTRICT
) ENGINE = InnoDB;

-- Every stock change, written by trg_menu_stock_log.
-- change_amount is negative when stock goes down.
CREATE TABLE inventory_transactions (
    txn_id        INT AUTO_INCREMENT PRIMARY KEY,
    item_id       INT         NOT NULL,
    order_id      INT         NULL,          -- NULL for restocks
    change_amount INT         NOT NULL,
    reason        VARCHAR(50) NOT NULL,
    created_at    TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_txn_change CHECK (change_amount <> 0),
    CONSTRAINT fk_txn_item FOREIGN KEY (item_id)
        REFERENCES menu_items (item_id) ON DELETE CASCADE,
    CONSTRAINT fk_txn_order FOREIGN KEY (order_id)
        REFERENCES orders (order_id) ON DELETE SET NULL
) ENGINE = InnoDB;

CREATE INDEX idx_txn_item ON inventory_transactions (item_id, created_at);


DELIMITER //

-- ---------------------------------------------------------------------
-- Trigger 1 (BEFORE UPDATE): keep status in step with stock.
--   stock hits 0           -> 'sold_out'
--   sold_out item restocked -> 'available'
-- 'delisted' is never changed automatically.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_menu_stock_status
BEFORE UPDATE ON menu_items
FOR EACH ROW
BEGIN
    IF NEW.current_stock = 0 AND NEW.status = 'available' THEN
        SET NEW.status = 'sold_out';
    ELSEIF NEW.current_stock > 0 AND OLD.status = 'sold_out' AND NEW.status = 'sold_out' THEN
        SET NEW.status = 'available';
    END IF;
END //

-- ---------------------------------------------------------------------
-- Trigger 2 (AFTER UPDATE): log every stock change.
-- Before changing stock, the caller sets two session variables:
--   @txn_reason   'order_placed', 'order_cancelled', 'restock', ...
--   @txn_order_id the order that caused it, or NULL
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_menu_stock_log
AFTER UPDATE ON menu_items
FOR EACH ROW
BEGIN
    IF NEW.current_stock <> OLD.current_stock THEN
        INSERT INTO inventory_transactions (item_id, order_id, change_amount, reason)
        VALUES (NEW.item_id,
                @txn_order_id,
                NEW.current_stock - OLD.current_stock,
                COALESCE(@txn_reason, 'manual_adjustment'));
    END IF;
END //

-- ---------------------------------------------------------------------
-- Function order_total: total of an order from its line items.
-- ---------------------------------------------------------------------
CREATE FUNCTION order_total(p_order_id INT)
RETURNS DECIMAL(10, 2)
READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(10, 2);
    SELECT COALESCE(SUM(quantity * price_at_order), 0) INTO v_total
    FROM order_items
    WHERE order_id = p_order_id;
    RETURN v_total;
END //

-- ---------------------------------------------------------------------
-- place_order: all-or-nothing order placement.
--   p_items is a JSON array: '[{"item_id":1,"quantity":2}, ...]'
--   1. student must exist, be active, and have < 3 open orders
--   2. lock the menu rows (SELECT ... FOR UPDATE) so two students
--      can't both take the last portion
--   3. every item must exist, be available, and have enough stock;
--      otherwise SIGNAL e.g. 'Not enough Samosa (only 2 left)'
--   4. insert the order + items, deduct stock (trigger logs it),
--      set the total with order_total()
-- Any error rolls back everything.
-- ---------------------------------------------------------------------
CREATE PROCEDURE place_order(
    IN  p_student_id INT,
    IN  p_canteen_id INT,
    IN  p_items      LONGTEXT,
    OUT p_order_id   INT
)
BEGIN
    DECLARE v_role   VARCHAR(20) DEFAULT NULL;
    DECLARE v_active BOOLEAN DEFAULT FALSE;
    DECLARE v_open   INT DEFAULT 0;
    DECLARE v_lines  INT DEFAULT 0;
    DECLARE v_locked INT DEFAULT 0;
    DECLARE v_name   VARCHAR(100) DEFAULT NULL;
    DECLARE v_stock  INT DEFAULT NULL;
    DECLARE v_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_msg    VARCHAR(255);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET @txn_reason = NULL, @txn_order_id = NULL;
        DROP TEMPORARY TABLE IF EXISTS tmp_cart;
        RESIGNAL;
    END;

    SET p_order_id = NULL;

    IF p_items IS NULL OR JSON_VALID(p_items) = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Order items are not valid JSON';
    END IF;

    -- READ COMMITTED: after waiting for a row lock, we read the latest
    -- committed stock. So the second of two students racing for the last
    -- portion gets a clean 'sold out' message, not a snapshot error.
    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    START TRANSACTION;

    -- 1. the student
    SELECT role, is_active INTO v_role, v_active
    FROM users WHERE user_id = p_student_id;

    IF v_role IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'User not found';
    END IF;
    IF v_role <> 'student' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only students can place orders';
    END IF;
    IF NOT v_active THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'This account is disabled';
    END IF;

    SELECT COUNT(*) INTO v_open
    FROM orders
    WHERE student_id = p_student_id
      AND status IN ('placed', 'preparing', 'ready');
    IF v_open >= 3 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'You already have 3 open orders. Please collect them first.';
    END IF;

    -- the cart, one row per item (duplicate lines are added together)
    DROP TEMPORARY TABLE IF EXISTS tmp_cart;
    CREATE TEMPORARY TABLE tmp_cart AS
        SELECT jt.item_id, SUM(jt.quantity) AS quantity
        FROM JSON_TABLE(p_items, '$[*]' COLUMNS (
                 item_id  INT PATH '$.item_id',
                 quantity INT PATH '$.quantity'
             )) AS jt
        GROUP BY jt.item_id;

    SELECT COUNT(*) INTO v_lines FROM tmp_cart;
    IF v_lines = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Your cart is empty';
    END IF;
    IF EXISTS (SELECT 1 FROM tmp_cart
               WHERE item_id IS NULL OR quantity IS NULL OR quantity < 1) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Every item needs an item_id and a quantity of at least 1';
    END IF;
    IF EXISTS (SELECT 1 FROM tmp_cart WHERE quantity > 10) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'You can order at most 10 of any one item';
    END IF;

    -- 2. lock the needed menu rows, in id order (avoids deadlocks)
    SELECT COUNT(*) INTO v_locked
    FROM (
        SELECT m.item_id
        FROM menu_items m
        WHERE m.canteen_id = p_canteen_id
          AND m.item_id IN (SELECT item_id FROM tmp_cart)
        ORDER BY m.item_id
        FOR UPDATE
    ) AS locked_rows;

    -- 3a. every item must exist in this canteen
    IF v_locked < v_lines THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Some items in your cart are not on this menu';
    END IF;

    -- 3b. every item must be available
    SET v_name = NULL;
    SELECT m.name, m.status INTO v_name, v_status
    FROM menu_items m
    WHERE m.item_id IN (SELECT item_id FROM tmp_cart)
      AND m.status <> 'available'
    ORDER BY m.name
    LIMIT 1;
    IF v_name IS NOT NULL THEN
        SET v_msg = IF(v_status = 'sold_out',
                       CONCAT(v_name, ' is sold out'),
                       CONCAT(v_name, ' is no longer on the menu'));
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    -- 3c. enough stock for every item
    SET v_name = NULL;
    SELECT m.name, m.current_stock INTO v_name, v_stock
    FROM menu_items m
    JOIN tmp_cart c ON c.item_id = m.item_id
    WHERE m.current_stock < c.quantity
    ORDER BY m.name
    LIMIT 1;
    IF v_name IS NOT NULL THEN
        SET v_msg = CONCAT('Not enough ', v_name, ' (only ', v_stock, ' left)');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    -- 4. create the order
    INSERT INTO orders (student_id, canteen_id) VALUES (p_student_id, p_canteen_id);
    SET p_order_id = LAST_INSERT_ID();

    INSERT INTO order_items (order_id, item_id, quantity, price_at_order)
    SELECT p_order_id, m.item_id, c.quantity, m.price
    FROM tmp_cart c
    JOIN menu_items m ON m.item_id = c.item_id;

    SET @txn_reason = 'order_placed', @txn_order_id = p_order_id;
    UPDATE menu_items m
    JOIN tmp_cart c ON c.item_id = m.item_id
    SET m.current_stock = m.current_stock - c.quantity;

    UPDATE orders SET total = order_total(p_order_id) WHERE order_id = p_order_id;

    COMMIT;
    SET @txn_reason = NULL, @txn_order_id = NULL;
    DROP TEMPORARY TABLE IF EXISTS tmp_cart;
END //

-- ---------------------------------------------------------------------
-- cancel_order: cancel an order and give back the stock it took.
--   placed / preparing / ready -> stock restored, status 'cancelled'
--   completed / cancelled      -> error
-- Stock is restored from inventory_transactions (what was really
-- deducted for this order). Who may cancel is checked by the backend.
-- ---------------------------------------------------------------------
CREATE PROCEDURE cancel_order(IN p_order_id INT)
BEGIN
    DECLARE v_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_msg    VARCHAR(255);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET @txn_reason = NULL, @txn_order_id = NULL;
        DROP TEMPORARY TABLE IF EXISTS tmp_refund;
        RESIGNAL;
    END;

    SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
    START TRANSACTION;

    SELECT status INTO v_status
    FROM orders WHERE order_id = p_order_id
    FOR UPDATE;

    IF v_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Order not found';
    END IF;
    IF v_status IN ('completed', 'cancelled') THEN
        SET v_msg = CONCAT('Cannot cancel an order that is ', v_status);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    -- copy the amounts out first: the trigger inserts into
    -- inventory_transactions, so the UPDATE can't read it directly
    DROP TEMPORARY TABLE IF EXISTS tmp_refund;
    CREATE TEMPORARY TABLE tmp_refund AS
        SELECT item_id, SUM(change_amount) AS net_change
        FROM inventory_transactions
        WHERE order_id = p_order_id
        GROUP BY item_id
        HAVING SUM(change_amount) <> 0;

    SET @txn_reason = 'order_cancelled', @txn_order_id = p_order_id;
    UPDATE menu_items m
    JOIN tmp_refund t ON t.item_id = m.item_id
    SET m.current_stock = m.current_stock - t.net_change;   -- net_change is negative

    UPDATE orders SET status = 'cancelled' WHERE order_id = p_order_id;

    COMMIT;
    SET @txn_reason = NULL, @txn_order_id = NULL;
    DROP TEMPORARY TABLE IF EXISTS tmp_refund;
END //

DELIMITER ;


-- =====================================================================
-- MANOJ: report views
-- =====================================================================
CREATE VIEW v_available_items AS
SELECT m.item_id, m.canteen_id, c.name AS canteen_name, c.location,
       m.name, m.description, m.category, m.price, m.current_stock,
       m.low_stock_threshold, m.status, m.created_at
FROM menu_items AS m
JOIN canteens AS c ON c.canteen_id = m.canteen_id
WHERE m.status = 'available';

CREATE VIEW v_sales_report AS
SELECT DATE(o.created_at) AS sale_date, m.category,
       SUM(oi.quantity * oi.price_at_order) AS sales_total,
       SUM(oi.quantity) AS items_sold,
       COUNT(DISTINCT o.order_id) AS order_count
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN menu_items AS m ON m.item_id = oi.item_id
WHERE o.payment_status = 'paid'
GROUP BY DATE(o.created_at), m.category;

CREATE VIEW v_low_stock AS
SELECT m.item_id, m.name, m.category, c.name AS canteen_name,
       m.current_stock, m.low_stock_threshold, m.status
FROM menu_items AS m
JOIN canteens AS c ON c.canteen_id = m.canteen_id
WHERE m.current_stock <= m.low_stock_threshold;

CREATE VIEW v_unpaid_orders AS
SELECT o.order_id, o.student_id, u.name AS student_name,
       o.canteen_id, c.name AS canteen_name, o.status, o.payment_status,
       o.total, o.created_at, o.updated_at
FROM orders AS o
JOIN users AS u ON u.user_id = o.student_id
JOIN canteens AS c ON c.canteen_id = o.canteen_id
WHERE o.payment_status = 'unpaid' AND o.status <> 'cancelled';
-- =====================================================================
