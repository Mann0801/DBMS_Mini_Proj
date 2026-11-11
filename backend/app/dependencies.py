"""Staff PIN check. Every staff route depends on require_staff."""

import os
import secrets

from fastapi import Header, HTTPException


def require_staff(x_staff_pin: str | None = Header(default=None)):
    expected = os.getenv("STAFF_PIN", "")
    if not expected:
        raise HTTPException(500, "STAFF_PIN is not set in .env")
    # compare_digest takes the same time whether the PIN is right or wrong
    if not x_staff_pin or not secrets.compare_digest(x_staff_pin, expected):
        raise HTTPException(401, "Wrong or missing staff PIN")
