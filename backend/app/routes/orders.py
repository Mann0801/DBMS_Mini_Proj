"""Order and stock routes. Owner: Mann.

Students (logged in):
    POST /api/orders                    place an order
    GET  /api/orders/mine               my orders
    GET  /api/orders/{id}               one order (own only)
    POST /api/orders/{id}/cancel        cancel (own, while 'placed')
Staff / admin:
    GET   /api/staff/orders?status=     all orders
    POST  /api/staff/orders/{id}/cancel cancel any unfinished order
    PATCH /api/staff/orders/{id}/status next status only
    PATCH /api/staff/orders/{id}/paid   mark paid
    GET   /api/staff/stock              stock per menu item
    GET   /api/staff/stock/low          low-stock alerts
    PATCH /api/staff/stock/{item_id}    restock / adjust (logged)
    GET   /api/staff/stock/{item_id}/history
"""

from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field, model_validator

from ..database import get_db
from ..dependencies import current_user, require_staff, require_student
from ..services import order as order_service
from ..services import stock as stock_service

router = APIRouter(prefix="/api/orders", tags=["Orders (students)"])
staff_router = APIRouter(prefix="/api/staff", tags=["Orders & stock (staff)"],
                         dependencies=[Depends(require_staff)])


class OrderItemIn(BaseModel):
    item_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=10)


class OrderIn(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1, max_length=30)


class StatusIn(BaseModel):
    status: Literal["preparing", "ready", "completed"]


class StockChangeIn(BaseModel):
    amount: int = Field(ge=-1000, le=1000, description="positive to add, negative to remove")
    reason: Literal["restock", "wastage", "correction"] = "restock"

    @model_validator(mode="after")
    def check(self):
        if self.amount == 0:
            raise ValueError("amount cannot be 0")
        if self.reason == "restock" and self.amount < 0:
            raise ValueError("a restock must add stock; use wastage or correction to remove")
        return self


# ---------------------------------------------------------------- students

@router.post("", status_code=201)
def place_order(body: OrderIn, user=Depends(require_student)):
    with get_db() as conn:
        return order_service.place_order(conn, user["user_id"], [i.model_dump() for i in body.items])


@router.get("/mine")
def my_orders(user=Depends(require_student)):
    with get_db() as conn:
        return order_service.my_orders(conn, user["user_id"])


@router.get("/{order_id}")
def get_order(order_id: int = Path(gt=0), user=Depends(current_user)):
    with get_db() as conn:
        return order_service.get_order_for(conn, order_id, user)


@router.post("/{order_id}/cancel")
def cancel_own_order(order_id: int = Path(gt=0), user=Depends(require_student)):
    with get_db() as conn:
        return order_service.cancel(conn, order_id, user)


# ---------------------------------------------------------------- staff: orders

@staff_router.get("/orders")
def list_orders(status: str | None = Query(default=None)):
    with get_db() as conn:
        return order_service.list_orders(conn, status)


@staff_router.post("/orders/{order_id}/cancel")
def staff_cancel(order_id: int = Path(gt=0), user=Depends(require_staff)):
    with get_db() as conn:
        return order_service.cancel(conn, order_id, user)


@staff_router.patch("/orders/{order_id}/status")
def update_status(body: StatusIn, order_id: int = Path(gt=0)):
    with get_db() as conn:
        return order_service.advance_status(conn, order_id, body.status)


@staff_router.patch("/orders/{order_id}/paid")
def mark_paid(order_id: int = Path(gt=0)):
    with get_db() as conn:
        return order_service.mark_paid(conn, order_id)


# ---------------------------------------------------------------- staff: stock

@staff_router.get("/stock")
def list_stock():
    with get_db() as conn:
        return stock_service.list_stock(conn)


# declared before /stock/{item_id}
@staff_router.get("/stock/low")
def low_stock():
    with get_db() as conn:
        return stock_service.low_stock(conn)


@staff_router.patch("/stock/{item_id}")
def change_stock(body: StockChangeIn, item_id: int = Path(gt=0)):
    with get_db() as conn:
        return stock_service.change_stock(conn, item_id, body.amount, body.reason)


@staff_router.get("/stock/{item_id}/history")
def stock_history(item_id: int = Path(gt=0)):
    with get_db() as conn:
        return stock_service.history(conn, item_id)
