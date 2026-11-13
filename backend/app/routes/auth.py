"""Sign-up, login, and admin user management. Owner: Mann."""

from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field, field_validator

from ..database import get_db
from ..dependencies import current_user, require_admin
from ..services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["Accounts"])
admin_router = APIRouter(prefix="/api/admin", tags=["Admin"],
                         dependencies=[Depends(require_admin)])

PHONE_PATTERN = r"^[6-9][0-9]{9}$"
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=120, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=100)
    phone: str = Field(pattern=PHONE_PATTERN, description="10-digit Indian mobile number")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()


class StaffIn(SignupIn):
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=100)


class ActiveIn(BaseModel):
    is_active: bool


# ---------------------------------------------------------------- everyone

@router.post("/signup", status_code=201)
def signup(body: SignupIn):
    """Students create their own account, and are logged in straight away."""
    with get_db() as conn:
        auth_service.create_user(conn, body.name, body.email, body.password, body.phone, "student")
        return auth_service.login(conn, body.email, body.password)


@router.post("/login")
def login(body: LoginIn):
    with get_db() as conn:
        return auth_service.login(conn, body.email, body.password)


@router.get("/me")
def me(user=Depends(current_user)):
    return user


# ---------------------------------------------------------------- admin

@admin_router.post("/staff", status_code=201)
def create_staff(body: StaffIn):
    """Only an admin can create staff accounts."""
    with get_db() as conn:
        return auth_service.create_user(conn, body.name, body.email, body.password, body.phone, "staff")


@admin_router.get("/users")
def list_users(role: Literal["student", "staff", "admin"] | None = Query(default=None)):
    with get_db() as conn:
        return auth_service.list_users(conn, role)


@admin_router.patch("/users/{user_id}/active")
def set_active(body: ActiveIn, user_id: int = Path(gt=0), admin=Depends(require_admin)):
    with get_db() as conn:
        return auth_service.set_active(conn, user_id, body.is_active, admin["user_id"])
