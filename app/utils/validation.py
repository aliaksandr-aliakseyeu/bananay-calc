"""Validation utilities."""
from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')


async def check_unique_field(
    db: AsyncSession,
    model: type[T],
    field_name: str,
    field_value: Any,
    exclude_id: int | None = None,
    error_message: str | None = None
) -> None:
    """
    Check if a field value is unique in the database.

    Args:
        db: Database session
        model: SQLAlchemy model class
        field_name: Name of the field to check
        field_value: Value to check for uniqueness
        exclude_id: Optional ID to exclude from check (for updates)
        error_message: Custom error message

    Raises:
        HTTPException: If the value is not unique
    """
    if field_value is None:
        return

    field = getattr(model, field_name)
    query = select(model).where(field == field_value)

    if exclude_id is not None:
        query = query.where(model.id != exclude_id)

    result = await db.execute(query)
    if result.scalar_one_or_none():
        if error_message is None:
            error_message = f"{model.__name__} with this {field_name} already exists"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )


async def check_unique_fields(
    db: AsyncSession,
    model: type[T],
    fields: dict[str, Any],
    exclude_id: int | None = None
) -> None:
    """
    Check multiple fields for uniqueness.

    Args:
        db: Database session
        model: SQLAlchemy model class
        fields: Dictionary of field_name: field_value to check
        exclude_id: Optional ID to exclude from check (for updates)

    Raises:
        HTTPException: If any value is not unique
    """
    for field_name, field_value in fields.items():
        if field_value is not None:
            await check_unique_field(
                db=db,
                model=model,
                field_name=field_name,
                field_value=field_value,
                exclude_id=exclude_id
            )
