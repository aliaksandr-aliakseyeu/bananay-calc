"""Temperature mode endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import TemperatureMode, User
from app.dependencies import get_current_user
from app.schemas.temperature_mode import (TemperatureModeCreate,
                                          TemperatureModeResponse,
                                          TemperatureModeUpdate)

router = APIRouter(prefix="/temperature-modes", tags=["Temperature Modes"])


@router.get("", response_model=list[TemperatureModeResponse])
async def get_temperature_modes(
    db: Annotated[AsyncSession, Depends(get_db)],
    is_active: bool | None = None,
) -> list[TemperatureModeResponse]:
    """Get all temperature modes."""
    query = select(TemperatureMode).order_by(TemperatureMode.sort_order, TemperatureMode.name)
    if is_active is not None:
        query = query.where(TemperatureMode.is_active == is_active)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{temperature_mode_id}", response_model=TemperatureModeResponse)
async def get_temperature_mode(
    temperature_mode_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TemperatureModeResponse:
    """Get a temperature mode by ID."""
    result = await db.execute(
        select(TemperatureMode).where(TemperatureMode.id == temperature_mode_id)
    )
    db_temperature_mode = result.scalar_one_or_none()
    if not db_temperature_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Temperature mode not found")
    return db_temperature_mode


@router.post("", response_model=TemperatureModeResponse, status_code=status.HTTP_201_CREATED)
async def create_temperature_mode(
    temperature_mode: TemperatureModeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TemperatureModeResponse:
    """Create a new temperature mode."""
    if await db.execute(select(TemperatureMode).where(TemperatureMode.name == temperature_mode.name)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Temperature mode already exists")
    db_temperature_mode = TemperatureMode(**temperature_mode.model_dump())
    db.add(db_temperature_mode)
    await db.commit()
    await db.refresh(db_temperature_mode)
    return db_temperature_mode


@router.patch("/{temperature_mode_id}", response_model=TemperatureModeResponse, status_code=status.HTTP_200_OK)
async def update_temperature_mode(
    temperature_mode_id: int,
    temperature_mode: TemperatureModeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TemperatureModeResponse:
    """Update a temperature mode."""
    if await db.execute(select(TemperatureMode).where(TemperatureMode.name == temperature_mode.name)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Temperature mode already exists")
    result = await db.execute(
        select(TemperatureMode).where(TemperatureMode.id == temperature_mode_id)
    )
    db_temperature_mode = result.scalar_one_or_none()
    if not db_temperature_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Temperature mode not found")
    update_data = temperature_mode.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_temperature_mode, field, value)
    await db.commit()
    await db.refresh(db_temperature_mode)
    return db_temperature_mode


@router.delete("/{temperature_mode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_temperature_mode(
    temperature_mode_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a temperature mode."""
    result = await db.execute(
        select(TemperatureMode).where(TemperatureMode.id == temperature_mode_id)
    )
    db_temperature_mode = result.scalar_one_or_none()
    if not db_temperature_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Temperature mode not found")
    await db.delete(db_temperature_mode)
    await db.commit()
