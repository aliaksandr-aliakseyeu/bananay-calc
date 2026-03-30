"""Schemas for public landing endpoints."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class TrialDeliveryLeadRequest(BaseModel):
    """Request payload for trial delivery lead form."""

    name: str = Field(..., min_length=1, max_length=120)
    phone: str = Field(..., min_length=7, max_length=40)
    email: EmailStr

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        phone = value.strip()
        if not phone:
            raise ValueError("Phone number is required")
        if phone.count("+") > 1 or ("+" in phone and not phone.startswith("+")):
            raise ValueError("Invalid phone number format")
        if not re.fullmatch(r"\+?[0-9()\-\s]+", phone):
            raise ValueError("Invalid phone number format")
        digits_count = len(re.sub(r"\D", "", phone))
        if digits_count < 7 or digits_count > 15:
            raise ValueError("Phone number must contain 7 to 15 digits")
        return phone
