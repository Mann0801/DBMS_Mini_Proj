"""Staff routes. Every route here needs the X-Staff-Pin header."""

from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field

from ..database import get_db
from ..dependencies import require_staff
from ..services import inventory as inventory_service
from ..services import order as order_service

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

# TODO (Manoj): GET/POST /api/staff/food, PUT/DELETE /api/staff/food/{id}
#               (DELETE marks unavailable if the item has past orders)


# ---------------------------------------------------------------- stats (Manoj)

# TODO (Manoj): GET /api/staff/stats/... one endpoint per query
#               (CTE, RANK, running total, GROUP BY/HAVING, LEFT JOIN IS NULL,
#                subquery, INTERSECT/EXCEPT, views)
