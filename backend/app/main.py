"""CampusEats app entry point.

Run from the project root:
    uvicorn backend.app.main:app --reload
"""

from pathlib import Path

import pymysql
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .routes import auth, orders, public, staff

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(title="CampusEats", description="Canteen pre-ordering API")

# Mann
app.include_router(auth.router)
app.include_router(auth.admin_router)
app.include_router(orders.router)
app.include_router(orders.staff_router)
# Manoj
app.include_router(public.router)
app.include_router(staff.router)


# ---------------------------------------------------------------- error handlers

# MySQL/MariaDB error codes we turn into friendly messages
FK_PARENT_MISSING = 1452
FK_CHILD_EXISTS = 1451
DUPLICATE_KEY = 1062
SIGNAL_ERROR = 1644      # raised by SIGNAL in place_order / cancel_order
CHECK_FAILED = 4025      # MariaDB CHECK constraint
CHECK_FAILED_MYSQL = 3819


@app.exception_handler(pymysql.MySQLError)
async def mysql_error_handler(request: Request, exc: pymysql.MySQLError):
    code = exc.args[0] if exc.args else None
    message = exc.args[1] if len(exc.args) > 1 else str(exc)

    if code == SIGNAL_ERROR:
        # message written by our stored procedure, e.g. "Not enough Paneer ..."
        if message.endswith("not found"):
            status = 404
        elif message.startswith("Only students") or "disabled" in message:
            status = 403
        else:
            status = 409
        return JSONResponse(status_code=status, content={"detail": message})
    if code == DUPLICATE_KEY:
        detail = ("An account with this email already exists" if "email" in message
                  else "That name already exists")
        return JSONResponse(status_code=409, content={"detail": detail})
    if code in (CHECK_FAILED, CHECK_FAILED_MYSQL):
        return JSONResponse(status_code=400, content={"detail": f"Invalid value: {message}"})
    if code == FK_CHILD_EXISTS:
        return JSONResponse(
            status_code=409,
            content={"detail": "Cannot delete this: other records still use it"},
        )
    if code == FK_PARENT_MISSING:
        return JSONResponse(status_code=400, content={"detail": "Referenced record does not exist"})
    if isinstance(exc, pymysql.OperationalError) and code in (1045, 2003, 1049):
        return JSONResponse(status_code=503, content={"detail": "Cannot connect to the database"})

    print(f"Unhandled database error {code}: {message}")
    return JSONResponse(status_code=500, content={"detail": "Database error"})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Turn FastAPI's long validation output into one readable line."""
    parts = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path"))
        msg = err["msg"]
        if field == "phone" or field.endswith(".phone"):
            msg = "must be a 10-digit mobile number starting with 6-9"
        parts.append(f"{field}: {msg}" if field else msg)
    return JSONResponse(status_code=422, content={"detail": "; ".join(parts)})


# ---------------------------------------------------------------- frontend

@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/login.html")


@app.get("/staff", include_in_schema=False)
def staff_home():
    return RedirectResponse("/staff.html")


# mounted last so /api/... routes take priority
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
