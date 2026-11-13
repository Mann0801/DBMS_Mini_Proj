"""Public menu routes (Manoj). Order routes are in routes/orders.py (Mann)."""

from fastapi import APIRouter, Query

from ..database import get_db
from ..services import food as food_service

router = APIRouter(prefix="/api", tags=["Students"])

# ---------------------------------------------------------------- menu (Manoj)

@router.get("/menu")
def menu(q: str | None = Query(default=None, max_length=100),
         category: str | None = Query(default=None, max_length=50)):
    with get_db() as conn:
        return food_service.menu(conn, q, category)


@router.get("/menu/categories")
def categories():
    with get_db() as conn:
        return food_service.categories(conn)
