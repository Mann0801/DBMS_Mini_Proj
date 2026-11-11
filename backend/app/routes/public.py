"""Student routes. No PIN needed."""

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, Field, field_validator

from ..database import get_db
from ..services import order as order_service
from ..services import food as food_service

router = APIRouter(prefix="/api", tags=["Students"])

PHONE_PATTERN = r"^[6-9][0-9]{9}$"


# ---------------------------------------------------------------- request bodies

class OrderItemIn(BaseModel):
    food_item_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=order_service.MAX_PER_ITEM)


class OrderIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=PHONE_PATTERN, description="10-digit Indian mobile number")
    items: list[OrderItemIn] = Field(min_length=1, max_length=30)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v


# ---------------------------------------------------------------- menu (Manoj)

@router.get("/menu")
def menu(q: str | None = Query(default=None, max_length=100),
         category: int | None = Query(default=None, gt=0)):
    with get_db() as conn:
        return food_service.menu(conn, q, category)


@router.get("/categories")
def categories():
    with get_db() as conn:
        return food_service.categories(conn)


# ---------------------------------------------------------------- orders (Mann)

@router.post("/orders", status_code=201)
def place_order(body: OrderIn):
    with get_db() as conn:
        return order_service.place_order(
            conn, body.name, body.phone, [i.model_dump() for i in body.items]
        )


# must be declared before /orders/{order_id}
@router.get("/orders/lookup")
def lookup_orders(phone: str = Query(pattern=PHONE_PATTERN)):
    with get_db() as conn:
        return order_service.orders_for_phone(conn, phone)


@router.get("/orders/{order_id}")
def track_order(
    order_id: int = Path(gt=0),
    phone: str = Query(pattern=PHONE_PATTERN),
):
    with get_db() as conn:
        return order_service.track_order(conn, order_id, phone)
