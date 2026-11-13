"""Login checks used by routes. Owner: Mann.

Routes add one of these with Depends(...):
    current_user     any logged-in, active user
    require_student  role = student
    require_staff    role = staff or admin
    require_admin    role = admin
Each one returns the user dict (user_id, name, email, role, ...).
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .database import get_db
from .services import auth as auth_service


# reads "Authorization: Bearer <token>"; also adds the Authorize button in /docs
bearer = HTTPBearer(auto_error=False, description="Paste the token from /api/auth/login")


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(401, "Please log in")
    user_id = auth_service.read_token(creds.credentials.strip())
    if user_id is None:
        raise HTTPException(401, "Your login is invalid or has expired. Please log in again.")
    with get_db() as conn:
        user = auth_service.get_user(conn, user_id)
    if user is None or not user["is_active"]:
        raise HTTPException(401, "This account is no longer active")
    return user


def require_student(user=Depends(current_user)):
    if user["role"] != "student":
        raise HTTPException(403, "Only students can do this")
    return user


def require_staff(user=Depends(current_user)):
    if user["role"] not in ("staff", "admin"):
        raise HTTPException(403, "Staff only")
    return user


def require_admin(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    return user
