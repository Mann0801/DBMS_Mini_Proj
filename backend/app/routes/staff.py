"""Staff routes. Every route here needs the X-Staff-Pin header."""

from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field

from ..database import get_db
from ..dependencies import require_staff
from ..services import inventory as inventory_service
from ..services import order as order_service
from ..services import food as food_service
from ..services import stats as stats_service
from ..services import food_details as details_service

router = APIRouter(
    prefix="/api/staff",
    tags=["Staff"],
    dependencies=[Depends(require_staff)],
)


# ---------------------------------------------------------------- request bodies

class StatusIn(BaseModel):
    status: Literal["preparing", "ready", "collected"]


class IngredientIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=20, examples=["kg"])
    stock: float = Field(default=0, ge=0)
    low_stock_threshold: float = Field(default=0, ge=0)


class AddStockIn(BaseModel):
    amount: float = Field(gt=0, le=100000)


class FoodIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    price: float = Field(gt=0, le=999999.99)
    category_id: int = Field(gt=0)
    is_available: bool = True


# ---------------------------------------------------------------- orders (Mann)

@router.get("/orders")
def list_orders(status: str | None = Query(default=None)):
    with get_db() as conn:
        return order_service.list_orders(conn, status)


@router.post("/orders/{order_id}/accept")
def accept_order(order_id: int = Path(gt=0)):
    with get_db() as conn:
        return order_service.accept_order(conn, order_id)


@router.post("/orders/{order_id}/reject")
def reject_order(order_id: int = Path(gt=0)):
    with get_db() as conn:
        return order_service.reject_order(conn, order_id)


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int = Path(gt=0)):
    with get_db() as conn:
        return order_service.cancel_order(conn, order_id)


@router.patch("/orders/{order_id}/status")
def update_status(body: StatusIn, order_id: int = Path(gt=0)):
    with get_db() as conn:
        return order_service.advance_status(conn, order_id, body.status)


@router.patch("/orders/{order_id}/paid")
def mark_paid(order_id: int = Path(gt=0)):
    with get_db() as conn:
        return order_service.mark_paid(conn, order_id)


# ---------------------------------------------------------------- ingredients (Mann)

@router.get("/ingredients")
def list_ingredients():
    with get_db() as conn:
        return inventory_service.list_ingredients(conn)


# must be declared before /ingredients/{ingredient_id}
@router.get("/ingredients/low-stock")
def low_stock():
    with get_db() as conn:
        return inventory_service.low_stock(conn)


@router.get("/ingredients/dish-availability")
def dish_availability():
    with get_db() as conn:
        return inventory_service.dish_availability(conn)


@router.post("/ingredients", status_code=201)
def add_ingredient(body: IngredientIn):
    with get_db() as conn:
        return inventory_service.add_ingredient(
            conn, body.name.strip(), body.unit.strip(), body.stock, body.low_stock_threshold
        )


@router.patch("/ingredients/{ingredient_id}/stock")
def add_stock(body: AddStockIn, ingredient_id: int = Path(gt=0)):
    with get_db() as conn:
        return inventory_service.add_stock(conn, ingredient_id, body.amount)


@router.get("/ingredients/{ingredient_id}/transactions")
def ingredient_transactions(ingredient_id: int = Path(gt=0)):
    with get_db() as conn:
        return inventory_service.transactions(conn, ingredient_id)


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
        result = food_service.delete_food(conn, food_id)
        # (Mann) a dish removed from MariaDB also loses its MongoDB document.
        # Inside the with-block: if MongoDB fails, the SQL delete rolls back.
        if result["deleted"]:
            details_service.delete_details_if_any(food_id)
        return result


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
