# CampusEats v2 design

## ER diagram

```mermaid
erDiagram
    USERS ||--o{ ORDERS : places
    CANTEENS ||--o{ MENU_ITEMS : offers
    CANTEENS ||--o{ ORDERS : receives
    ORDERS ||--|{ ORDER_ITEMS : contains
    MENU_ITEMS ||--o{ ORDER_ITEMS : appears_in
    MENU_ITEMS ||--o{ INVENTORY_TRANSACTIONS : records
    ORDERS o|--o{ INVENTORY_TRANSACTIONS : may_cause

    USERS {
        int user_id PK
        varchar name
        varchar email UK
        varchar password_hash
        varchar role
        char phone
        boolean is_active
        timestamp created_at
    }
    CANTEENS {
        int canteen_id PK
        varchar name UK
        varchar location
    }
    MENU_ITEMS {
        int item_id PK
        int canteen_id FK
        varchar name
        varchar description
        varchar category
        decimal price
        int current_stock
        int low_stock_threshold
        varchar status
        timestamp created_at
    }
    ORDERS {
        int order_id PK
        int student_id FK
        int canteen_id FK
        varchar status
        varchar payment_status
        decimal total
        timestamp created_at
        timestamp updated_at
    }
    ORDER_ITEMS {
        int order_id PK, FK
        int item_id PK, FK
        int quantity
        decimal price_at_order
    }
    INVENTORY_TRANSACTIONS {
        int txn_id PK
        int item_id FK
        int order_id FK
        int change_amount
        varchar reason
        timestamp created_at
    }
```

Primary keys are identified by `PK` in the ERD and underlined in the relational schema below. `INVENTORY_TRANSACTIONS.order_id` is nullable for restocks and other non-order stock changes. MongoDB dish details are outside this relational ER diagram.

## Relational schema

- USERS(<u>user_id</u> PK, name, email UNIQUE, password_hash, role, phone, is_active, created_at)
- CANTEENS(<u>canteen_id</u> PK, name UNIQUE, location)
- MENU_ITEMS(<u>item_id</u> PK, canteen_id FK → CANTEENS.canteen_id, name, description, category, price, current_stock, low_stock_threshold, status, created_at, UNIQUE(canteen_id, name))
- ORDERS(<u>order_id</u> PK, student_id FK → USERS.user_id, canteen_id FK → CANTEENS.canteen_id, status, payment_status, total, created_at, updated_at)
- ORDER_ITEMS(<u>order_id</u> PK/FK → ORDERS.order_id, <u>item_id</u> PK/FK → MENU_ITEMS.item_id, quantity, price_at_order)
- INVENTORY_TRANSACTIONS(<u>txn_id</u> PK, item_id FK → MENU_ITEMS.item_id, order_id nullable FK → ORDERS.order_id, change_amount, reason, created_at)

```mermaid
flowchart LR
  ORDERS -->|student_id| USERS
  MENU_ITEMS -->|canteen_id| CANTEENS
  ORDERS -->|canteen_id| CANTEENS
  ORDER_ITEMS -->|order_id| ORDERS
  ORDER_ITEMS -->|item_id| MENU_ITEMS
  INVENTORY_TRANSACTIONS -->|item_id| MENU_ITEMS
  INVENTORY_TRANSACTIONS -. nullable order_id .-> ORDERS
```

## Technology justification

MariaDB is the relational engine because it is installed by default on Fedora and supports the project's CTEs, window functions, `INTERSECT`/`EXCEPT`, stored procedures, triggers, and FULLTEXT search. The design moved from PostgreSQL to MariaDB to match the required Fedora default and the agreed setup. MongoDB stores flexible dish-specific details because attributes can vary by dish. FastAPI with PyMySQL provides a small Python API using parameterized raw SQL, while plain HTML, CSS, and JavaScript keep the frontend framework-free and are served directly by FastAPI.
