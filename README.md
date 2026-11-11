# CampusEats

CampusEats is a small campus canteen ordering application. It uses FastAPI and MariaDB for its API and data, with plain HTML, CSS, and JavaScript pages for students and staff.

## Requirements

- Python 3.10 or newer
- MariaDB 11.8
- A browser

Install Python packages from the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Database setup

Review `database/setup.sql` and set the database user's password to match the value you intend to use in `.env`. Run setup as a MariaDB administrator:

```sh
sudo mariadb < database/setup.sql
```

Copy `.env.example` to `.env` and set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `STAFF_PIN`. The sample setup uses `campuseats` and `change_me`; change the password in both places before using the application.

Load the schema and sample data:

```sh
mariadb -u campuseats -p campuseats < database/schema.sql
mariadb -u campuseats -p campuseats < database/seed.sql
```

**Warning:** `database/schema.sql` drops and recreates the project's tables, views, trigger, and procedures. Use it only when setting up or intentionally resetting a development database. `database/seed_temp.sql` is older temporary data; use `database/seed.sql` for the complete sample menu.

## Run the application

From the repository root, with the virtual environment active and `.env` configured:

```sh
uvicorn backend.app.main:app --reload
```

Open `http://127.0.0.1:8000/` for student ordering, `http://127.0.0.1:8000/staff` for the PIN-protected staff page, and `http://127.0.0.1:8000/docs` for interactive API documentation. The application uses the existing Uvicorn command and default port 8000.

## API endpoints

All responses are JSON. Staff endpoints require the `X-Staff-Pin` header configured by `STAFF_PIN`.

### Student endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/menu?q=&category=` | Available menu; optional text query and category ID |
| GET | `/api/categories` | List menu categories |
| POST | `/api/orders` | Place an order with `name`, `phone`, and item IDs/quantities |
| GET | `/api/orders/{order_id}?phone=` | Track an order using its order number and phone |
| GET | `/api/orders/lookup?phone=` | List orders for a phone number |

### Staff food and statistics endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET, POST | `/api/staff/food` | List and add food items |
| PUT, DELETE | `/api/staff/food/{food_id}` | Edit or delete a food item; items with order history are made unavailable |
| GET | `/api/staff/stats/daily-sales` | Paid sales by day for the last seven days |
| GET | `/api/staff/stats/top-items` | Ranked food items by paid units sold |
| GET | `/api/staff/stats/running-total` | Running paid-sales total by day |
| GET | `/api/staff/stats/category-sales` | Paid sales grouped by category |
| GET | `/api/staff/stats/never-ordered` | Food items with no order-item rows |
| GET | `/api/staff/stats/above-average-orders` | Orders above the average order value |
| GET | `/api/staff/stats/shared-ingredients` | Ingredients used by multiple dishes |
| GET | `/api/staff/stats/single-dish-ingredients` | Ingredients used by only one dish |
| GET | `/api/staff/stats/item-sales` | Item sales including zero-sales items |
| GET | `/api/staff/stats/reports/sales` | `v_sales_report` view |
| GET | `/api/staff/stats/reports/low-stock` | `v_low_stock` view |
| GET | `/api/staff/stats/reports/unpaid-orders` | `v_unpaid_orders` view |
| GET | `/api/staff/stats/reports/top-items` | `v_top_items` view |

Order workflow, ingredient stock, and existing PIN-protected endpoints are implemented in their existing Mann-owned files and are also listed in `/docs`.

## Database objects and SQL features

Manoj's section of `database/schema.sql` defines `categories` and `food_items`, preserving the columns referenced by order processing. The food table has a MariaDB FULLTEXT index over `name` and `description`. Menu searches use `LIKE` for queries of three characters or fewer and `MATCH ... AGAINST` for longer queries.

The original project plan requires exactly these four report views:

- `v_sales_report`: paid sales by date and category.
- `v_low_stock`: ingredients at or below their low-stock threshold.
- `v_unpaid_orders`: unpaid orders.
- `v_top_items`: paid quantities and sales per food item, including items with no paid sales so the report can rank all menu items.

The statistics service demonstrates the requested SQL features: a recursive CTE for seven calendar days, `RANK()` and running `SUM() OVER` windows, category `GROUP BY`/`HAVING`, `LEFT JOIN`/`IS NULL`, an average-value subquery, `INTERSECT`, `EXCEPT`, and `COALESCE` for zero-sales items. Food and statistics queries use bound parameters where they accept user input.

`database/seed.sql` supplies five categories, fifteen food items, fifteen ingredients, a recipe for every menu item, and three sample orders.
