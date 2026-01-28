"""Producer tutorial schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import TutorialStatus, TutorialType


class TutorialBase(BaseModel):
    """Base schema for Tutorial."""

    tutorial_type: TutorialType = Field(
        ..., description="Type of tutorial"
    )


class TutorialCreate(TutorialBase):
    """Schema for creating a tutorial."""

    pass


class TutorialUpdate(BaseModel):
    """Schema for updating a tutorial."""

    status: TutorialStatus | None = Field(
        None, description="Tutorial completion status"
    )
    current_step: int | None = Field(
        None, ge=0, description="Current step in the tutorial"
    )
    last_shown_at: datetime | None = Field(
        None, description="Last time tutorial was shown"
    )


class TutorialStatusUpdate(BaseModel):
    """Schema for updating tutorial status."""

    status: TutorialStatus = Field(
        ..., description="New tutorial status"
    )


class TutorialResponse(TutorialBase):
    """Schema for tutorial response."""

    id: int
    producer_id: int
    status: TutorialStatus
    current_step: int
    started_at: datetime | None
    completed_at: datetime | None
    last_shown_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TutorialsSummaryResponse(BaseModel):
    """Summary of all tutorials for a producer."""

    show_tooltips: bool = Field(
        ..., description="Whether to show tooltips/tutorials"
    )
    tutorials: list[TutorialResponse] = Field(
        ..., description="List of all tutorials"
    )
    all_completed: bool = Field(
        ..., description="Whether all tutorials are completed"
    )
    completion_percentage: int = Field(
        ..., ge=0, le=100, description="Percentage of completed tutorials"
    )


class TooltipsToggleRequest(BaseModel):
    """Request to toggle tooltips visibility."""

    show_tooltips: bool = Field(
        ..., description="Whether to show tooltips"
    )


class TutorialResetRequest(BaseModel):
    """Request to reset tutorials."""

    tutorial_type: TutorialType | None = Field(
        None, description="Specific tutorial to reset, or None to reset all"
    )
