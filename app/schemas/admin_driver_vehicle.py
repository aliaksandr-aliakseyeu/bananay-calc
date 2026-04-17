"""Admin schemas for driver vehicle moderation."""

from pydantic import BaseModel, Field, field_validator


class AdminDriverVehicleRejectBody(BaseModel):
    """Reject vehicle verification (required reason for driver UI)."""

    reason: str = Field(..., max_length=2000)

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("reason must not be empty")
        return s
