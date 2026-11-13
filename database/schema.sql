-- =====================================================================
-- CampusEats schema (MariaDB 11 / MySQL 8 compatible)
-- Load with:  mariadb -u campuseats -p campuseats < database/schema.sql
-- Re-running this file drops and recreates everything.
--
-- Sections:
--   MANN  : orders, order_items, ingredients, recipes,
--           inventory_transactions, trigger, accept_order, cancel_order
--   MANOJ : categories, food_items, views
-- Only edit your own section.
-- =====================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ---------- drop everything (safe to re-run) ----------
DROP VIEW IF EXISTS v_sales_report;
DROP VIEW IF EXISTS v_low_stock;
DROP VIEW IF EXISTS v_unpaid_orders;
DROP VIEW IF EXISTS v_top_items;

DROP PROCEDURE IF EXISTS accept_order;
DROP PROCEDURE IF EXISTS cancel_order;
DROP FUNCTION IF EXISTS order_total;
DROP FUNCTION IF EXISTS portions_available;
DROP TRIGGER IF EXISTS trg_ingredients_stock_log;

DROP TABLE IF EXISTS inventory_transactions;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS recipes;
DROP TABLE IF EXISTS ingredients;
DROP TABLE IF EXISTS food_items;
DROP TABLE IF EXISTS categories;

SET FOREIGN_KEY_CHECKS = 1;


-- =====================================================================
-- MANOJ: menu tables
-- Mann's tables reference food_items(id), name, price and is_available.
-- =====================================================================

CREATE TABLE categories (
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
) ENGINE = InnoDB;

CREATE TABLE food_items (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(100)  NOT NULL,
    description  VARCHAR(255),
    price        DECIMAL(8, 2) NOT NULL,
    is_available BOOLEAN       NOT NULL DEFAULT TRUE,
    category_id  INT           NOT NULL,
    created_at   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_food_category FOREIGN KEY (category_id) REFERENCES categories (id),
    FULLTEXT KEY ft_food_name_description (name, description)
) ENGINE = InnoDB;


-- =====================================================================
-- MANN: ingredients, recipes, orders, stock log
-- =====================================================================

CREATE TABLE ingredients (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    name                VARCHAR(100)   NOT NULL UNIQUE,
    unit                VARCHAR(20)    NOT NULL,          -- kg, litre, pcs ...
    stock               DECIMAL(10, 3) NOT NULL DEFAULT 0,
    low_stock_threshold DECIMAL(10, 3) NOT NULL DEFAULT 0,
    CONSTRAINT chk_ingredient_stock     CHECK (stock >= 0),
    CONSTRAINT chk_ingredient_threshold CHECK (low_stock_threshold >= 0)
) ENGINE = InnoDB;

-- Which ingredients one portion of a dish needs.
CREATE TABLE recipes (
    food_item_id    INT            NOT NULL,
    ingredient_id   INT            NOT NULL,
    quantity_needed DECIMAL(10, 3) NOT NULL,
    PRIMARY KEY (food_item_id, ingredient_id),
    CONSTRAINT chk_recipe_qty CHECK (quantity_needed > 0),
    CONSTRAINT fk_recipe_food FOREIGN KEY (food_item_id)
        REFERENCES food_items (id) ON DELETE CASCADE,
    CONSTRAINT fk_recipe_ingredient FOREIGN KEY (ingredient_id)
        REFERENCES ingredients (id)
) ENGINE = InnoDB;

CREATE TABLE orders (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    customer_name  VARCHAR(100)   NOT NULL,
    customer_phone CHAR(10)       NOT NULL,
    status         VARCHAR(20)    NOT NULL DEFAULT 'placed',
    payment_status VARCHAR(10)    NOT NULL DEFAULT 'unpaid',
    total          DECIMAL(10, 2) NOT NULL DEFAULT 0,
    created_at     TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_order_status CHECK (status IN
        ('placed', 'accepted', 'preparing', 'ready', 'collected', 'rejected')),
    CONSTRAINT chk_payment_status CHECK (payment_status IN ('unpaid', 'paid')),
    -- 10-digit Indian mobile number: starts with 6, 7, 8 or 9
    CONSTRAINT chk_customer_phone CHECK (customer_phone REGEXP '^[6-9][0-9]{9}$'),
    CONSTRAINT chk_customer_name CHECK (CHAR_LENGTH(TRIM(customer_name)) > 0),
    CONSTRAINT chk_order_total CHECK (total >= 0)
) ENGINE = InnoDB;

CREATE INDEX idx_orders_phone  ON orders (customer_phone);
CREATE INDEX idx_orders_status ON orders (status);

-- price = snapshot of food_items.price when the order was placed
CREATE TABLE order_items (
    order_id     INT           NOT NULL,
    food_item_id INT           NOT NULL,
    quantity     INT           NOT NULL,
    price        DECIMAL(8, 2) NOT NULL,
    PRIMARY KEY (order_id, food_item_id),
    CONSTRAINT chk_item_qty   CHECK (quantity > 0),
    CONSTRAINT chk_item_price CHECK (price >= 0),
    CONSTRAINT fk_item_order FOREIGN KEY (order_id)
        REFERENCES orders (id) ON DELETE CASCADE,
    -- no cascade: a food item with past orders cannot be deleted
    CONSTRAINT fk_item_food FOREIGN KEY (food_item_id)
        REFERENCES food_items (id)
) ENGINE = InnoDB;

-- Every stock change, written by the trigger below.
-- change_amount is negative when stock goes down.
CREATE TABLE inventory_transactions (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    ingredient_id INT            NOT NULL,
    order_id      INT            NULL,
    change_amount DECIMAL(10, 3) NOT NULL,
    reason        VARCHAR(50)    NOT NULL,
    created_at    TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_txn_ingredient FOREIGN KEY (ingredient_id)
        REFERENCES ingredients (id) ON DELETE CASCADE,
    CONSTRAINT fk_txn_order FOREIGN KEY (order_id)
        REFERENCES orders (id) ON DELETE SET NULL
) ENGINE = InnoDB;

CREATE INDEX idx_txn_ingredient ON inventory_transactions (ingredient_id, created_at);


DELIMITER //

-- ---------------------------------------------------------------------
-- Trigger: log every stock change.
-- Before updating stock, the caller sets two session variables:
--   @txn_reason   e.g. 'order_accepted', 'order_cancelled', 'restock'
--   @txn_order_id the order that caused it, or NULL
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_ingredients_stock_log
AFTER UPDATE ON ingredients
FOR EACH ROW
BEGIN
    IF NEW.stock <> OLD.stock THEN
        INSERT INTO inventory_transactions (ingredient_id, order_id, change_amount, reason)
        VALUES (NEW.id,
                @txn_order_id,
                NEW.stock - OLD.stock,
                COALESCE(@txn_reason, 'manual_adjustment'));
    END IF;
END //

-- ---------------------------------------------------------------------
-- accept_order: all-or-nothing stock deduction.
--   1. order must exist and be 'placed'
--   2. lock the needed ingredient rows (SELECT ... FOR UPDATE)
--   3. if any ingredient is short -> SIGNAL 'Not enough <name> ...'
--   4. deduct stock (trigger logs it), set status = 'accepted'
-- Any error rolls the whole thing back.
-- ---------------------------------------------------------------------
CREATE PROCEDURE accept_order(IN p_order_id INT)
BEGIN
    DECLARE v_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_short  VARCHAR(100) DEFAULT NULL;
    DECLARE v_locked INT DEFAULT 0;
    DECLARE v_msg    VARCHAR(255);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET @txn_reason = NULL, @txn_order_id = NULL;
        RESIGNAL;
    END;

    START TRANSACTION;

    -- 1. lock and check the order
    SELECT status INTO v_status
    FROM orders WHERE id = p_order_id
    FOR UPDATE;

    IF v_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Order not found';
    END IF;

    IF v_status <> 'placed' THEN
        SET v_msg = CONCAT('Only placed orders can be accepted (this order is ', v_status, ')');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    -- 2. lock every ingredient this order needs, in id order (avoids deadlocks)
    SELECT COUNT(*) INTO v_locked
    FROM (
        SELECT i.id
        FROM ingredients i
        WHERE i.id IN (SELECT r.ingredient_id
                       FROM order_items oi
                       JOIN recipes r ON r.food_item_id = oi.food_item_id
                       WHERE oi.order_id = p_order_id)
        ORDER BY i.id
        FOR UPDATE
    ) AS locked_rows;

    -- 3. find the first ingredient that is short
    SELECT i.name INTO v_short
    FROM ingredients i
    JOIN (SELECT r.ingredient_id, SUM(r.quantity_needed * oi.quantity) AS needed
          FROM order_items oi
          JOIN recipes r ON r.food_item_id = oi.food_item_id
          WHERE oi.order_id = p_order_id
          GROUP BY r.ingredient_id) AS need ON need.ingredient_id = i.id
    WHERE i.stock < need.needed
    ORDER BY i.name
    LIMIT 1;

    IF v_short IS NOT NULL THEN
        SET v_msg = CONCAT('Not enough ', v_short, ' to accept this order');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    -- 4. deduct stock; the trigger writes inventory_transactions
    SET @txn_reason = 'order_accepted', @txn_order_id = p_order_id;

    UPDATE ingredients i
    JOIN (SELECT r.ingredient_id, SUM(r.quantity_needed * oi.quantity) AS needed
          FROM order_items oi
          JOIN recipes r ON r.food_item_id = oi.food_item_id
          WHERE oi.order_id = p_order_id
          GROUP BY r.ingredient_id) AS need ON need.ingredient_id = i.id
    SET i.stock = i.stock - need.needed;

    UPDATE orders SET status = 'accepted' WHERE id = p_order_id;

    COMMIT;
    SET @txn_reason = NULL, @txn_order_id = NULL;
END //

-- ---------------------------------------------------------------------
-- cancel_order: cancel an order and give back any stock it took.
--   placed                       -> rejected (no stock was taken)
--   accepted/preparing/ready     -> stock restored, then rejected
--   collected/rejected           -> error
-- Stock is restored from inventory_transactions (what was really
-- deducted), so later recipe edits don't affect the refund.
-- ---------------------------------------------------------------------
CREATE PROCEDURE cancel_order(IN p_order_id INT)
BEGIN
    DECLARE v_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_msg    VARCHAR(255);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET @txn_reason = NULL, @txn_order_id = NULL;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT status INTO v_status
    FROM orders WHERE id = p_order_id
    FOR UPDATE;

    IF v_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Order not found';
    END IF;

    IF v_status IN ('collected', 'rejected') THEN
        SET v_msg = CONCAT('Cannot cancel an order that is ', v_status);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    IF v_status IN ('accepted', 'preparing', 'ready') THEN
        -- Copy the amounts out first: the trigger inserts into
        -- inventory_transactions, so the UPDATE can't read it directly.
        DROP TEMPORARY TABLE IF EXISTS tmp_refund;
        CREATE TEMPORARY TABLE tmp_refund AS
            SELECT ingredient_id, SUM(change_amount) AS net_change
            FROM inventory_transactions
            WHERE order_id = p_order_id
            GROUP BY ingredient_id
            HAVING SUM(change_amount) <> 0;

        SET @txn_reason = 'order_cancelled', @txn_order_id = p_order_id;

        -- net change for this order is negative; add it back
        UPDATE ingredients i
        JOIN tmp_refund t ON t.ingredient_id = i.id
        SET i.stock = i.stock - t.net_change;

        DROP TEMPORARY TABLE tmp_refund;
    END IF;

    UPDATE orders SET status = 'rejected' WHERE id = p_order_id;

    COMMIT;
    SET @txn_reason = NULL, @txn_order_id = NULL;
END //

-- ---------------------------------------------------------------------
-- Function order_total: total of an order from its line items.
-- Used by the backend right after an order's items are inserted.
-- ---------------------------------------------------------------------
CREATE FUNCTION order_total(p_order_id INT)
RETURNS DECIMAL(10, 2)
READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(10, 2);
    SELECT COALESCE(SUM(quantity * price), 0) INTO v_total
    FROM order_items
    WHERE order_id = p_order_id;
    RETURN v_total;
END //

-- ---------------------------------------------------------------------
-- Function portions_available: how many portions of a dish the current
-- stock can make = the smallest FLOOR(stock / needed) over its recipe.
-- Returns NULL if the dish has no recipe.
-- ---------------------------------------------------------------------
CREATE FUNCTION portions_available(p_food_item_id INT)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_portions INT;
    SELECT MIN(FLOOR(i.stock / r.quantity_needed)) INTO v_portions
    FROM recipes r
    JOIN ingredients i ON i.id = r.ingredient_id
    WHERE r.food_item_id = p_food_item_id;
    RETURN v_portions;
END //

DELIMITER ;


-- =====================================================================
-- MANOJ: report views
-- =====================================================================

CREATE OR REPLACE VIEW v_sales_report AS
SELECT DATE(o.created_at) AS sale_date,
       c.id AS category_id,
       c.name AS category_name,
       SUM(oi.quantity * oi.price) AS sales_total,
       SUM(oi.quantity) AS items_sold,
       COUNT(DISTINCT o.id) AS order_count
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
JOIN food_items f ON f.id = oi.food_item_id
JOIN categories c ON c.id = f.category_id
WHERE o.payment_status = 'paid'
GROUP BY DATE(o.created_at), c.id, c.name;

CREATE OR REPLACE VIEW v_low_stock AS
SELECT id, name, unit, stock, low_stock_threshold
FROM ingredients
WHERE stock <= low_stock_threshold;

CREATE OR REPLACE VIEW v_unpaid_orders AS
SELECT id, customer_name, customer_phone, status, total, created_at
FROM orders
WHERE payment_status = 'unpaid';

CREATE OR REPLACE VIEW v_top_items AS
SELECT f.id AS food_item_id, f.name, c.name AS category_name,
       COALESCE(SUM(CASE WHEN o.payment_status = 'paid' THEN oi.quantity ELSE 0 END), 0) AS units_sold,
       COALESCE(SUM(CASE WHEN o.payment_status = 'paid' THEN oi.quantity * oi.price ELSE 0 END), 0) AS sales_total
FROM food_items f
JOIN categories c ON c.id = f.category_id
LEFT JOIN order_items oi ON oi.food_item_id = f.id
LEFT JOIN orders o ON o.id = oi.order_id
GROUP BY f.id, f.name, c.name;
