"""Dish details routes (MongoDB). Owner: Mann.

Anyone (menu page):
    GET    /api/menu-details                  read all, optional filters
    GET    /api/menu-details/{item_id}        read one
Staff / admin:
    GET    /api/staff/menu-details/summary    aggregation pipeline
    PUT    /api/staff/menu-details/{item_id}  create or update ($set, upsert)
    PATCH  /api/staff/menu-details/{item_id}/special     set or clear ($unset)
    POST   /api/staff/menu-details/{item_id}/tags        add a tag ($addToSet)
    DELETE /api/staff/menu-details/{item_id}/tags/{tag}  remove a tag ($pull)
    DELETE /api/staff/menu-details/{item_id}  delete the document
"""

from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field, field_validator

from ..database import get_db
from ..dependencies import require_staff
from ..services import menu_details as details_service

Dietary = Literal["veg", "vegan", "egg", "non-veg"]

public_router = APIRouter(prefix="/api/menu-details", tags=["Dish details (MongoDB)"])
staff_router = APIRouter(prefix="/api/staff/menu-details", tags=["Dish details (MongoDB)"],
                         dependencies=[Depends(require_staff)])


class DetailsIn(BaseModel):
    dietary: Dietary
    spice_level: int = Field(ge=0, le=3)
    allergens: list[str] = Field(default_factory=list, max_length=10)
    tags: list[str] = Field(default_factory=list, max_length=10)
    calories: int | None = Field(default=None, ge=0, le=5000)
    special_note: str | None = Field(default=None, max_length=200)
    extra: dict[str, str | int | float | bool] | None = Field(
        default=None, description='Any other fields, e.g. {"served": "hot"}')

    @field_validator("allergens", "tags")
    @classmethod
    def short_words(cls, values):
        if any(len(v) > 30 for v in values):
            raise ValueError("each entry must be 30 characters or less")
        return values

    @field_validator("extra")
    @classmethod
    def safe_extra_keys(cls, extra):
        for key in extra or {}:
            # block Mongo operators ($...), dotted paths and our own field names
            if (key in details_service.CORE_FIELDS or key.startswith("$")
                    or "." in key or not key.strip() or len(key) > 30):
                raise ValueError(f"'{key}' cannot be used as an extra field name")
        return extra


class SpecialIn(BaseModel):
    note: str | None = Field(default=None, max_length=200)


class TagIn(BaseModel):
    tag: str = Field(min_length=1, max_length=30)


# ---------------------------------------------------------------- read

@public_router.get("")
def list_details(
    dietary: Dietary | None = None,
    exclude_allergen: str | None = Query(default=None, max_length=30),
    max_spice: int | None = Query(default=None, ge=0, le=3),
    tag: str | None = Query(default=None, max_length=30),
):
    return details_service.list_details(dietary, exclude_allergen, max_spice, tag)


@public_router.get("/{item_id}")
def get_details(item_id: int = Path(gt=0)):
    return details_service.get_details(item_id)


# ---------------------------------------------------------------- staff

@staff_router.get("/summary")
def summary():
    return details_service.summary()


@staff_router.put("/{item_id}")
def save_details(body: DetailsIn, item_id: int = Path(gt=0)):
    with get_db() as conn:  # checks the dish exists in MariaDB
        return details_service.save_details(conn, item_id, body.model_dump())


@staff_router.patch("/{item_id}/special")
def set_special(body: SpecialIn, item_id: int = Path(gt=0)):
    return details_service.set_special(item_id, body.note.strip() if body.note else None)


@staff_router.post("/{item_id}/tags")
def add_tag(body: TagIn, item_id: int = Path(gt=0)):
    return details_service.change_tag(item_id, body.tag, add=True)


@staff_router.delete("/{item_id}/tags/{tag}")
def remove_tag(item_id: int = Path(gt=0), tag: str = Path(min_length=1, max_length=30)):
    return details_service.change_tag(item_id, tag, add=False)


@staff_router.delete("/{item_id}")
def delete_details(item_id: int = Path(gt=0)):
    return details_service.delete_details(item_id)
