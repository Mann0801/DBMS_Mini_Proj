-- CampusEats sample data. Load after database/schema.sql on a fresh schema:
--   mariadb -u campuseats -p campuseats < database/seed.sql

INSERT INTO categories (id, name) VALUES
    (1, 'Snacks'),
    (2, 'Meals'),
    (3, 'Wraps & Sandwiches'),
    (4, 'Beverages'),
    (5, 'Desserts');

INSERT INTO food_items (id, name, description, price, category_id) VALUES
    (1, 'Samosa', 'Crisp pastry with spiced potato filling', 18.00, 1),
    (2, 'Veg Puff', 'Flaky pastry filled with vegetables', 22.00, 1),
    (3, 'Aloo Tikki', 'Golden potato patties with chutney', 30.00, 1),
    (4, 'Veg Thali', 'Rice, dal, seasonal vegetables and roti', 95.00, 2),
    (5, 'Rajma Chawal', 'Kidney bean curry served with rice', 85.00, 2),
    (6, 'Paneer Biryani', 'Fragrant rice with spiced paneer', 120.00, 2),
    (7, 'Dal Khichdi', 'Comforting lentil and rice khichdi', 75.00, 2),
    (8, 'Paneer Wrap', 'Spiced paneer wrapped with vegetables', 80.00, 3),
    (9, 'Veg Frankie', 'Vegetable filling in a soft flatbread', 65.00, 3),
    (10, 'Grilled Sandwich', 'Grilled bread with vegetables and cheese', 70.00, 3),
    (11, 'Masala Chai', 'Milk tea brewed with warming spices', 18.00, 4),
    (12, 'Cold Coffee', 'Chilled milk coffee', 45.00, 4),
    (13, 'Mango Lassi', 'Yogurt drink blended with mango', 50.00, 4),
    (14, 'Gulab Jamun', 'Soft milk dumplings in sugar syrup', 35.00, 5),
    (15, 'Chocolate Brownie', 'Rich cocoa brownie', 45.00, 5);

INSERT INTO ingredients (id, name, unit, stock, low_stock_threshold) VALUES
    (1, 'Potato', 'kg', 8.000, 1.000),
    (2, 'Flour', 'kg', 7.000, 1.000),
    (3, 'Cooking Oil', 'L', 5.000, 1.000),
    (4, 'Paneer', 'kg', 3.000, 0.500),
    (5, 'Rice', 'kg', 10.000, 2.000),
    (6, 'Kidney Beans', 'kg', 4.000, 1.000),
    (7, 'Lentils', 'kg', 4.000, 1.000),
    (8, 'Tomato', 'kg', 4.000, 1.000),
    (9, 'Onion', 'kg', 4.000, 1.000),
    (10, 'Mixed Spices', 'kg', 1.000, 0.200),
    (11, 'Bread', 'loaf', 12.000, 2.000),
    (12, 'Tea Leaves', 'kg', 1.000, 0.200),
    (13, 'Milk', 'L', 12.000, 2.000),
    (14, 'Sugar', 'kg', 5.000, 1.000),
    (15, 'Cocoa', 'kg', 2.000, 0.300);

-- Quantities are required per one serving; every food item has a recipe.
INSERT INTO recipes (food_item_id, ingredient_id, quantity_needed) VALUES
    (1, 1, 0.060), (1, 2, 0.035), (1, 3, 0.020), (1, 10, 0.003),
    (2, 1, 0.040), (2, 2, 0.045), (2, 9, 0.010),
    (3, 1, 0.120), (3, 3, 0.015), (3, 10, 0.004),
    (4, 5, 0.120), (4, 7, 0.050), (4, 2, 0.060), (4, 8, 0.030),
    (5, 5, 0.140), (5, 6, 0.080), (5, 8, 0.040), (5, 9, 0.020),
    (6, 5, 0.160), (6, 4, 0.080), (6, 9, 0.020), (6, 10, 0.005),
    (7, 5, 0.080), (7, 7, 0.060), (7, 3, 0.010),
    (8, 4, 0.100), (8, 2, 0.060), (8, 9, 0.015), (8, 10, 0.004),
    (9, 1, 0.050), (9, 2, 0.055), (9, 9, 0.015), (9, 10, 0.003),
    (10, 11, 0.100), (10, 4, 0.030), (10, 1, 0.040),
    (11, 12, 0.003), (11, 13, 0.120), (11, 14, 0.008),
    (12, 13, 0.200), (12, 14, 0.012), (12, 15, 0.004),
    (13, 13, 0.150), (13, 14, 0.010),
    (14, 2, 0.025), (14, 13, 0.015), (14, 14, 0.030),
    (15, 2, 0.030), (15, 13, 0.020), (15, 14, 0.020), (15, 15, 0.015);

INSERT INTO orders (id, customer_name, customer_phone, status, payment_status, total) VALUES
    (1, 'Aarav Shah', '9876543210', 'collected', 'paid', 131.00),
    (2, 'Priya Nair', '9123456780', 'accepted', 'unpaid', 160.00),
    (3, 'Kabir Rao', '9988776655', 'placed', 'unpaid', 75.00);

INSERT INTO order_items (order_id, food_item_id, quantity, price) VALUES
    (1, 1, 2, 18.00), (1, 4, 1, 95.00),
    (2, 8, 2, 80.00),
    (3, 11, 1, 18.00), (3, 14, 1, 35.00), (3, 2, 1, 22.00);
