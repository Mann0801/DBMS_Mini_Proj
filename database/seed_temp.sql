-- TEMPORARY test data so the order/stock logic can be tested early.
-- Manoj's database/seed.sql replaces this file.
-- Load with:  mariadb -u campuseats -p campuseats < database/seed_temp.sql

INSERT INTO categories (id, name) VALUES
    (1, 'Snacks'),
    (2, 'Meals');

INSERT INTO food_items (id, name, description, price, category_id) VALUES
    (1, 'Samosa',      'Crispy potato samosa',         15.00, 1),
    (2, 'Paneer Wrap', 'Paneer tikka in a soft wrap',  70.00, 1),
    (3, 'Veg Thali',   'Rice, dal, sabzi, 2 rotis',    90.00, 2);

INSERT INTO ingredients (id, name, unit, stock, low_stock_threshold) VALUES
    (1, 'Potato',   'kg',  5.000, 1.000),
    (2, 'Flour',    'kg',  4.000, 1.000),
    (3, 'Oil',      'L',   3.000, 0.500),
    (4, 'Paneer',   'kg',  0.250, 0.500),   -- deliberately low
    (5, 'Tortilla', 'pcs', 10.000, 5.000),
    (6, 'Rice',     'kg',  6.000, 2.000),
    (7, 'Dal',      'kg',  3.000, 1.000);

-- quantity per ONE portion
INSERT INTO recipes (food_item_id, ingredient_id, quantity_needed) VALUES
    (1, 1, 0.050), (1, 2, 0.030), (1, 3, 0.020),   -- Samosa
    (2, 4, 0.100), (2, 5, 1.000), (2, 3, 0.010),   -- Paneer Wrap
    (3, 6, 0.150), (3, 7, 0.080), (3, 2, 0.060);   -- Veg Thali

-- Order 1: 4 samosas + 1 thali  -> enough stock, should accept
-- Order 2: 5 paneer wraps       -> needs 0.5 kg paneer, only 0.25 -> must fail
INSERT INTO orders (id, customer_name, customer_phone, total) VALUES
    (1, 'Aarav Shah',  '9876543210', 150.00),
    (2, 'Priya Nair',  '9123456780', 350.00);

INSERT INTO order_items (order_id, food_item_id, quantity, price) VALUES
    (1, 1, 4, 15.00),
    (1, 3, 1, 90.00),
    (2, 2, 5, 70.00);
