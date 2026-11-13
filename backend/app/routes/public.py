"""Public menu routes (Manoj).

TODO (Manoj, v2): switch food.py to the menu_items table
(category is a text column now) and the /api/menu/categories path.
Order routes moved to routes/orders.py (Mann).
"""

from fastapi import APIRouter, Query

from ..database import get_db
from ..services import food as food_service

router = APIRouter(prefix="/api", tags=["Students"])

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
