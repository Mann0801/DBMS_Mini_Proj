# CampusEats v2

CampusEats is a single-canteen ordering app. MariaDB stores accounts, menu, orders, and stock history; MongoDB stores flexible dish details. FastAPI serves the API and the plain HTML/CSS/JavaScript frontend.

## Setup

Requirements: Python 3.10+, MariaDB, and Podman (or Docker) for MongoDB.

```sh
git fetch
git checkout v2
git pull
sudo mariadb < database/setup.sql
cp .env.example .env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mariadb -u campuseats -pchange_me campuseats < database/schema.sql
mariadb -u campuseats -pchange_me campuseats < database/seed.sql
podman run -d --name campuseats-mongo -p 127.0.0.1:27017:27017 docker.io/library/mongo:7
database/mongo/setup.sh
```

On Windows or macOS, use `docker` in place of `podman`. Start MongoDB before running `database/mongo/setup.sh`; it creates the validated `menu_details` collection, indexes, and one details document per menu item. Configure `.env` with the MariaDB and MongoDB settings expected by the backend. `database/reset.sh` reloads MariaDB and refreshes MongoDB demo details. The schema drops and recreates its tables, procedures, triggers, and views; use reset only for development data.

## Run

From the project root with the virtual environment active:

```sh
uvicorn backend.app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) for the student page, [http://localhost:8000/docs](http://localhost:8000/docs) for API docs, and `/staff` for the staff page.

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@campuseats.test` | `Admin@123` |
| Staff | `staff1@campuseats.test` | `Staff@123` |
| Staff | `staff2@campuseats.test` | `Staff@123` |
| Student | `student1@campuseats.test` through `student6@campuseats.test` | `Student@123` |

## API overview

| Method and route | Use |
| --- | --- |
| `GET /api/menu?q=&category=` | Available menu; short search terms use `LIKE`, longer terms use Boolean FULLTEXT prefixes |
| `GET /api/menu/categories` | Distinct menu categories |
| `GET /api/staff/menu` | Staff menu, including non-available statuses |
| `POST /api/staff/menu` | Add a menu item with starting stock |
| `PUT /api/staff/menu/{item_id}` | Edit item details and status without changing stock |
| `DELETE /api/staff/menu/{item_id}` | Delete an unused item or delist one with order history |
| `GET /api/staff/stats/...` | Sales, order, stock, student set-operation, and view reports |

Order, account, and stock routes are implemented in Mann's backend sections. The student UI uses `POST /api/orders`, `GET /api/orders/mine`, and `POST /api/orders/{id}/cancel`.

## SQL features demonstrated

- `FULLTEXT` index on menu item name, description, and category; Boolean prefix search in the public menu route.
- Recursive CTE for a seven-day calendar series, including dates with no paid orders.
- `RANK()` for item popularity; `SUM() OVER` for running daily sales; `ROW_NUMBER() OVER (PARTITION BY category)` for category spenders.
- `GROUP BY` and `HAVING` for category sales; `LEFT JOIN ... IS NULL` for never-ordered items.
- Nested average-value query excluding cancelled orders on both sides.
- `INTERSECT` and `EXCEPT` compare the ordered menu items of two selected students.
- `COALESCE` supplies zero totals where sales data is absent.
- Views: `v_available_items`, `v_sales_report` (paid orders grouped by date and category), `v_low_stock`, and `v_unpaid_orders`.
- `place_order` and `cancel_order` procedures atomically change stock; triggers log stock movements and maintain sold-out status.

The complete relational design, ER diagram, and technology rationale are in [docs/design.md](docs/design.md). Run [database/queries_demo.sql](database/queries_demo.sql) during the viva to demonstrate DML and every Manoj stats query.
