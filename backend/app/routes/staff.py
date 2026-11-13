"""Staff menu and stats routes (Manoj). Need a staff or admin login.

TODO (Manoj, v2): switch food.py / stats.py to the v2 tables
(menu_items, users, orders) and rename /food to /menu.
Order and stock routes moved to routes/orders.py and routes/stock.py (Mann).
"""

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field

from ..database import get_db
from ..dependencies import require_staff
from ..services import food as food_service
from ..services import stats as stats_service

router = APIRouter(
    prefix="/api/staff",
    tags=["Staff"],
    dependencies=[Depends(require_staff)],
)


# ---------------------------------------------------------------- request bodies

class FoodIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    price: float = Field(gt=0, le=999999.99)
    category_id: int = Field(gt=0)
    is_available: bool = True


# ---------------------------------------------------------------- food items (Manoj)

@router.get("/food")
def list_food():
    with get_db() as conn:
        return food_service.list_food(conn)


@router.post("/food", status_code=201)
def create_food(body: FoodIn):
    with get_db() as conn:
        return food_service.create_food(
            conn, body.name.strip(), body.description.strip() if body.description else None,
            body.price, body.category_id, body.is_available,
        )


@router.put("/food/{food_id}")
def update_food(body: FoodIn, food_id: int = Path(gt=0)):
    with get_db() as conn:
        return food_service.update_food(
            conn, food_id, body.name.strip(), body.description.strip() if body.description else None,
            body.price, body.category_id, body.is_available,
        )


@router.delete("/food/{food_id}")
def delete_food(food_id: int = Path(gt=0)):
    with get_db() as conn:
        return food_service.delete_food(conn, food_id)


# ---------------------------------------------------------------- stats (Manoj)

@router.get("/stats/daily-sales")
def stats_daily_sales():
    with get_db() as conn:
        return stats_service.daily_sales(conn)


@router.get("/stats/top-items")
def stats_top_items():
    with get_db() as conn:
        return stats_service.top_items(conn)


@router.get("/stats/running-total")
def stats_running_total():
    with get_db() as conn:
        return stats_service.running_sales(conn)


@router.get("/stats/category-sales")
def stats_category_sales():
    with get_db() as conn:
        return stats_service.category_sales(conn)


@router.get("/stats/never-ordered")
def stats_never_ordered():
    with get_db() as conn:
        return stats_service.never_ordered(conn)


@router.get("/stats/above-average-orders")
def stats_above_average_orders():
    with get_db() as conn:
        return stats_service.above_average_orders(conn)


@router.get("/stats/shared-ingredients")
def stats_shared_ingredients():
    with get_db() as conn:
        return stats_service.shared_ingredients(conn)


@router.get("/stats/single-dish-ingredients")
def stats_single_dish_ingredients():
    with get_db() as conn:
        return stats_service.single_dish_ingredients(conn)


@router.get("/stats/item-sales")
def stats_item_sales():
    with get_db() as conn:
        return stats_service.item_sales(conn)


@router.get("/stats/reports/sales")
def stats_sales_report():
    with get_db() as conn:
        return stats_service.sales_report(conn)


@router.get("/stats/reports/low-stock")
def stats_low_stock_report():
    with get_db() as conn:
        return stats_service.low_stock(conn)


@router.get("/stats/reports/unpaid-orders")
def stats_unpaid_orders_report():
    with get_db() as conn:
        return stats_service.unpaid_orders(conn)


@router.get("/stats/reports/top-items")
def stats_top_items_report():
    with get_db() as conn:
        return stats_service.view_top_items(conn)
