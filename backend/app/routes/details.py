"""Dish details routes (MongoDB). Owner: Mann.

Public (students):
    GET    /api/food-details                 read all, with optional filters
    GET    /api/food-details/{id}            read one
Staff (PIN):
    GET    /api/staff/food-details/summary   aggregation pipeline
    PUT    /api/staff/food-details/{id}      create or update a dish's document
    PATCH  /api/staff/food-details/{id}/special    set or clear today's special
    POST   /api/staff/food-details/{id}/tags       add a tag    ($addToSet)
    DELETE /api/staff/food-details/{id}/tags/{tag} remove a tag ($pull)
    DELETE /api/staff/food-details/{id}      delete the document
"""

from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field, field_validator

from ..database import get_db
from ..dependencies import require_staff
from ..services import food_details as details_service

Dietary = Literal["veg", "vegan", "egg", "non-veg"]

public_router = APIRouter(prefix="/api/food-details", tags=["Dish details (MongoDB)"])
staff_router = APIRouter(
    prefix="/api/staff/food-details",
    tags=["Dish details (MongoDB)"],
    dependencies=[Depends(require_staff)],
)


class DetailsIn(BaseModel):
    dietary: Dietary
    spice_level: int = Field(ge=0, le=3)
    allergens: list[str] = Field(default_factory=list, max_length=10)
    tags: list[str] = Field(default_factory=list, max_length=10)
    calories: int | None = Field(default=None, ge=0, le=5000)
    special_note: str | None = Field(default=None, max_length=200)
    extra: dict[str, str | int | float | bool] | None = Field(
        default=None, description="Any other fields, e.g. {\"served\": \"hot\"}"
    )

    @field_validator("allergens", "tags")
    @classmethod
    def short_words(cls, values):
        for v in values:
            if len(v) > 30:
                raise ValueError("each entry must be 30 characters or less")
        return values

    @field_validator("extra")
    @classmethod
    def safe_extra_keys(cls, extra):
        for key in extra or {}:
            if (key in details_service.CORE_FIELDS or key.startswith("$")
                    or "." in key or not key.strip() or len(key) > 30):
                raise ValueError(f"'{key}' cannot be used as an extra field name")
        return extra


class SpecialIn(BaseModel):
    note: str | None = Field(default=None, max_length=200)


class TagIn(BaseModel):
    tag: str = Field(min_length=1, max_length=30)


# ---------------------------------------------------------------- read (public)

@public_router.get("")
def list_details(
    dietary: Dietary | None = None,
    exclude_allergen: str | None = Query(default=None, max_length=30),
    max_spice: int | None = Query(default=None, ge=0, le=3),
    tag: str | None = Query(default=None, max_length=30),
):
    return details_service.list_details(dietary, exclude_allergen, max_spice, tag)


@public_router.get("/{food_id}")
def get_details(food_id: int = Path(gt=0)):
    return details_service.get_details(food_id)


# ---------------------------------------------------------------- staff

@staff_router.get("/summary")
def summary():
    return details_service.summary()


@staff_router.put("/{food_id}")
def save_details(body: DetailsIn, food_id: int = Path(gt=0)):
    with get_db() as conn:  # used to check the dish exists in MariaDB
        return details_service.save_details(conn, food_id, body.model_dump())


@staff_router.patch("/{food_id}/special")
def set_special(body: SpecialIn, food_id: int = Path(gt=0)):
    note = body.note.strip() if body.note else None
    return details_service.set_special(food_id, note)


@staff_router.post("/{food_id}/tags")
def add_tag(body: TagIn, food_id: int = Path(gt=0)):
    return details_service.change_tag(food_id, body.tag, add=True)


@staff_router.delete("/{food_id}/tags/{tag}")
def remove_tag(food_id: int = Path(gt=0), tag: str = Path(min_length=1, max_length=30)):
    return details_service.change_tag(food_id, tag, add=False)


@staff_router.delete("/{food_id}")
def delete_details(food_id: int = Path(gt=0)):
    return details_service.delete_details(food_id)
