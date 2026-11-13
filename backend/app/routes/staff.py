"""Staff menu and statistics routes, protected by Mann's staff role check."""

from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field

from ..database import get_db
from ..dependencies import require_staff
from ..services import food as food_service
from ..services import menu_details as details_service
from ..services import stats as stats_service

router = APIRouter(prefix="/api/staff", tags=["Staff"], dependencies=[Depends(require_staff)])


class MenuCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    category: str = Field(min_length=1, max_length=50)
    price: float = Field(gt=0, le=999999.99)
    current_stock: int = Field(ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)


class MenuUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    category: str = Field(min_length=1, max_length=50)
    price: float = Field(gt=0, le=999999.99)
    status: Literal["available", "sold_out", "delisted"]


@router.get("/students")
def list_students():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, name FROM users WHERE role='student' AND is_active=TRUE ORDER BY name")
            return cur.fetchall()


@router.get("/menu")
def list_menu():
    with get_db() as conn:
        return food_service.list_food(conn)


@router.post("/menu", status_code=201)
def create_menu_item(body: MenuCreateIn):
    with get_db() as conn:
        return food_service.create_food(
            conn, body.name.strip(), body.description.strip() if body.description else None,
            body.category.strip(), body.price, body.current_stock, body.low_stock_threshold,
        )


@router.put("/menu/{item_id}")
def update_menu_item(body: MenuUpdateIn, item_id: int = Path(gt=0)):
    with get_db() as conn:
        return food_service.update_food(
            conn, item_id, body.name.strip(), body.description.strip() if body.description else None,
            body.category.strip(), body.price, body.status,
        )


@router.delete("/menu/{item_id}")
def delete_menu_item(item_id: int = Path(gt=0)):
    with get_db() as conn:
        result = food_service.delete_food(conn, item_id)
        if result["deleted"]:
            details_service.delete_details_if_any(item_id)
        return result


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


@router.get("/stats/student-items/both")
def stats_student_items_both(student_a: int = Query(gt=0), student_b: int = Query(gt=0)):
    with get_db() as conn:
        return stats_service.student_item_set(conn, student_a, student_b, "both")


@router.get("/stats/student-items/a-only")
def stats_student_items_a_only(student_a: int = Query(gt=0), student_b: int = Query(gt=0)):
    with get_db() as conn:
        return stats_service.student_item_set(conn, student_a, student_b, "a_only")


@router.get("/stats/top-spenders-by-category")
def stats_top_spenders_by_category():
    with get_db() as conn:
        return stats_service.top_spenders_by_category(conn)


@router.get("/stats/reports/available-items")
def stats_available_items_report():
    with get_db() as conn:
        return stats_service.available_view(conn)


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
