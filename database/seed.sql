-- Complete v2 demo data. Load after database/schema.sql.

INSERT INTO canteens (canteen_id, name, location)
VALUES (1, 'Main Canteen', 'Block A, Ground Floor');

INSERT INTO users (user_id, name, email, password_hash, role, phone) VALUES
(1,'Canteen Admin','admin@campuseats.test','pbkdf2_sha256$200000$b4f9e78ecf88e773$VPHi0LeE3GrAjND9RGCPcVCFk7sXJUB7T0iMe0eGnQk=','admin',NULL),
(2,'Ravi Kumar','staff1@campuseats.test','pbkdf2_sha256$200000$b0c9490cee171265$9KnqJusZaQGsSVXN9BjMVWJUvwqBES91mSXCZOWHWAI=','staff','9811111111'),
(3,'Meera Das','staff2@campuseats.test','pbkdf2_sha256$200000$05dc06aa13bee2fb$zpnvsgVtgk5MXOpIbPnuQuCCLz3MqAOAUmZX2Px6ED8=','staff','9822222222'),
(4,'Aarav Shah','student1@campuseats.test','pbkdf2_sha256$200000$401466a922019ea6$l23yuP+58XuQgwN3rR1m7yV2US2dp1lFJkHT40KfMUU=','student','9876543210'),
(5,'Priya Nair','student2@campuseats.test','pbkdf2_sha256$200000$ee19b8959e20431b$PStJcCJsMggPng/3diLXCjpN1P6DD2n8YCYlsZjnvt4=','student','9123456780'),
(6,'Kabir Rao','student3@campuseats.test','pbkdf2_sha256$200000$d4e03e2ef6360512$0J2vi++nAJH0QFfWpHVTIEr8fbMlFrtXIBptJRTDAvo=','student','9988776655'),
(7,'Ananya Iyer','student4@campuseats.test','pbkdf2_sha256$200000$2f912618dbcc85b4$c4RpQ5TVBvzrsb24gCioqwK9QhsbqBV9fQEp6kRU+IE=','student','8765432109'),
(8,'Dev Patel','student5@campuseats.test','pbkdf2_sha256$200000$16bae4082b9e84a0$o+kAxGQKVISnm0asegdXMLXFte4pSNmfVNPMTAjaN78=','student','7654321098'),
(9,'Sana Ali','student6@campuseats.test','pbkdf2_sha256$200000$6371aa81d8281a3e$GqLWlCkkH8OFAgNvlfBFwbRRWGwQCl1nkG0EUzY3nqQ=','student','6543210987');

INSERT INTO menu_items (item_id,canteen_id,name,description,category,price,current_stock,low_stock_threshold,status) VALUES
(1,1,'Samosa','Crisp pastry with spiced potato filling','Snacks',18.00,40,10,'available'),
(2,1,'Veg Puff','Flaky pastry filled with vegetables','Snacks',22.00,18,5,'available'),
(3,1,'Aloo Tikki','Golden potato patties with chutney','Snacks',30.00,14,5,'available'),
(4,1,'Veg Thali','Rice, dal, seasonal vegetables and roti','Meals',95.00,22,5,'available'),
(5,1,'Rajma Chawal','Kidney bean curry served with rice','Meals',85.00,16,5,'available'),
(6,1,'Paneer Biryani','Fragrant rice with spiced paneer','Meals',120.00,12,4,'available'),
(7,1,'Dal Khichdi','Comforting lentil and rice khichdi','Meals',75.00,2,5,'available'),
(8,1,'Paneer Wrap','Spiced paneer wrapped with vegetables','Snacks',80.00,3,5,'available'),
(9,1,'Veg Frankie','Vegetable filling in a soft flatbread','Snacks',65.00,13,4,'available'),
(10,1,'Grilled Sandwich','Grilled bread with vegetables and cheese','Snacks',70.00,11,4,'available'),
(11,1,'Masala Chai','Milk tea brewed with warming spices','Beverages',18.00,50,10,'available'),
(12,1,'Cold Coffee','Chilled milk coffee','Beverages',45.00,24,6,'available'),
(13,1,'Mango Lassi','Yogurt drink blended with mango','Beverages',50.00,17,5,'available'),
(14,1,'Gulab Jamun','Soft milk dumplings in sugar syrup','Desserts',35.00,0,5,'sold_out'),
(15,1,'Chocolate Brownie','Rich cocoa brownie','Desserts',45.00,20,5,'available');

-- Orders are created through place_order so stock and inventory history agree.
CALL place_order(4,1,'[{"item_id":1,"quantity":2},{"item_id":11,"quantity":1}]',@o1);
CALL place_order(5,1,'[{"item_id":4,"quantity":1},{"item_id":8,"quantity":1}]',@o2);
CALL place_order(6,1,'[{"item_id":5,"quantity":1},{"item_id":12,"quantity":1}]',@o3);
CALL place_order(7,1,'[{"item_id":2,"quantity":2},{"item_id":13,"quantity":1}]',@o4);
CALL place_order(8,1,'[{"item_id":6,"quantity":1},{"item_id":3,"quantity":1}]',@o5);
CALL place_order(9,1,'[{"item_id":9,"quantity":1},{"item_id":11,"quantity":2}]',@o6);
CALL place_order(4,1,'[{"item_id":10,"quantity":1},{"item_id":15,"quantity":1}]',@o7);
CALL place_order(5,1,'[{"item_id":7,"quantity":1},{"item_id":1,"quantity":1}]',@o8);
CALL place_order(6,1,'[{"item_id":3,"quantity":1},{"item_id":12,"quantity":1}]',@o9);

UPDATE orders SET status='preparing' WHERE order_id=@o2;
UPDATE orders SET status='ready' WHERE order_id=@o3;
UPDATE orders SET status='completed', payment_status='paid' WHERE order_id IN (@o1,@o4,@o5);
UPDATE orders SET payment_status='paid' WHERE order_id=@o6;
CALL cancel_order(@o8);

UPDATE orders SET created_at=NOW()-INTERVAL 6 DAY WHERE order_id=@o1;
UPDATE orders SET created_at=NOW()-INTERVAL 5 DAY WHERE order_id=@o2;
UPDATE orders SET created_at=NOW()-INTERVAL 4 DAY WHERE order_id=@o3;
UPDATE orders SET created_at=NOW()-INTERVAL 3 DAY WHERE order_id=@o4;
UPDATE orders SET created_at=NOW()-INTERVAL 2 DAY WHERE order_id=@o5;
UPDATE orders SET created_at=NOW()-INTERVAL 1 DAY WHERE order_id=@o6;
UPDATE orders SET created_at=NOW() WHERE order_id IN (@o7,@o9);
