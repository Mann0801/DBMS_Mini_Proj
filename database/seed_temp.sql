-- TEMPORARY test data (Mann) so accounts, orders and stock can be tested
-- before the full database/seed.sql (Manoj) is ready.
-- Load after schema.sql:
--   mariadb -u campuseats -p campuseats < database/seed_temp.sql
--
-- Logins (password hashes made with pbkdf2_sha256, same as the backend):
--   admin@campuseats.test     Admin@123
--   staff1@campuseats.test    Staff@123
--   student1@campuseats.test  Student@123
--   student2@campuseats.test  Student@123

INSERT INTO canteens (canteen_id, name, location) VALUES
    (1, 'Main Canteen', 'Block A, Ground Floor');

INSERT INTO users (user_id, name, email, password_hash, role, phone) VALUES
    (1, 'Canteen Admin', 'admin@campuseats.test',
        'pbkdf2_sha256$200000$b4f9e78ecf88e773$VPHi0LeE3GrAjND9RGCPcVCFk7sXJUB7T0iMe0eGnQk=', 'admin', NULL),
    (2, 'Ravi (Staff)', 'staff1@campuseats.test',
        'pbkdf2_sha256$200000$b0c9490cee171265$9KnqJusZaQGsSVXN9BjMVWJUvwqBES91mSXCZOWHWAI=', 'staff', '9811111111'),
    (3, 'Aarav Shah', 'student1@campuseats.test',
        'pbkdf2_sha256$200000$401466a922019ea6$l23yuP+58XuQgwN3rR1m7yV2US2dp1lFJkHT40KfMUU=', 'student', '9876543210'),
    (4, 'Priya Nair', 'student2@campuseats.test',
        'pbkdf2_sha256$200000$ee19b8959e20431b$PStJcCJsMggPng/3diLXCjpN1P6DD2n8YCYlsZjnvt4=', 'student', '9123456780');

INSERT INTO menu_items (item_id, canteen_id, name, description, category, price, current_stock, low_stock_threshold) VALUES
    (1, 1, 'Samosa',      'Crispy potato samosa',        'Snacks',    15.00, 40, 10),
    (2, 1, 'Paneer Wrap', 'Paneer tikka in a soft wrap', 'Wraps',     70.00,  3,  5),   -- deliberately low
    (3, 1, 'Veg Thali',   'Rice, dal, sabzi, 2 rotis',   'Meals',     90.00, 20,  5),
    (4, 1, 'Masala Chai', 'Milk tea with spices',        'Beverages', 15.00, 50, 10),
    (5, 1, 'Gulab Jamun', 'Two soft gulab jamuns',       'Desserts',  30.00,  1,  5);   -- last one

-- Orders are placed THROUGH the procedure, so stock is deducted and
-- inventory_transactions is filled exactly like in the real app.
-- Format: CALL place_order(student_id, canteen_id, '<items JSON>', @order_id);

-- Order 1: Aarav, 2 samosa + 1 chai
CALL place_order(3, 1, '[{"item_id":1,"quantity":2},{"item_id":4,"quantity":1}]', @o1);

-- Order 2: Priya, 1 thali + 1 paneer wrap
CALL place_order(4, 1, '[{"item_id":3,"quantity":1},{"item_id":2,"quantity":1}]', @o2);

-- Move order 1 along and mark it paid, to have a finished example
UPDATE orders SET status = 'completed', payment_status = 'paid' WHERE order_id = @o1;
