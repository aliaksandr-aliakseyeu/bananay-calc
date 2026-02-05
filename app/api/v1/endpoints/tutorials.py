"""Producer tutorials endpoints."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import ProducerTutorial, TutorialStatus, TutorialType, User
from app.dependencies import get_current_verified_producer
from app.schemas.tutorial import (TooltipsToggleRequest, TutorialResetRequest,
                                  TutorialResponse, TutorialsSummaryResponse,
                                  TutorialStatusUpdate)

router = APIRouter(prefix="/tutorials", tags=["Tutorials"])


async def get_or_create_tutorial(
    db: AsyncSession,
    producer_id: int,
    tutorial_type: TutorialType,
) -> ProducerTutorial:
    """Get existing tutorial or create a new one."""
    result = await db.execute(
        select(ProducerTutorial).where(
            ProducerTutorial.producer_id == producer_id,
            ProducerTutorial.tutorial_type == tutorial_type,
        )
    )
    tutorial = result.scalar_one_or_none()

    if not tutorial:
        tutorial = ProducerTutorial(
            producer_id=producer_id,
            tutorial_type=tutorial_type,
            status=TutorialStatus.NOT_STARTED,
            current_step=0,
        )
        db.add(tutorial)
        await db.commit()
        await db.refresh(tutorial)

    return tutorial


@router.get("/", response_model=TutorialsSummaryResponse)
async def get_all_tutorials(
    current_user: Annotated[User, Depends(get_current_verified_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TutorialsSummaryResponse:
    """
    Get all tutorials for the current producer.

    Returns summary including completion status and tooltips visibility.
    Automatically creates tutorial records if they don't exist.
    """
    result = await db.execute(
        select(ProducerTutorial)
        .where(ProducerTutorial.producer_id == current_user.id)
        .order_by(ProducerTutorial.tutorial_type)
    )
    tutorials = result.scalars().all()
    
    existing_types = {t.tutorial_type for t in tutorials}
    missing_types = [tt for tt in TutorialType if tt not in existing_types]
    
    if missing_types:
        new_tutorials = [
            ProducerTutorial(
                producer_id=current_user.id,
                tutorial_type=tutorial_type,
                status=TutorialStatus.NOT_STARTED,
                current_step=0,
            )
            for tutorial_type in missing_types
        ]
        db.add_all(new_tutorials)
        await db.commit()
        
        result = await db.execute(
            select(ProducerTutorial)
            .where(
                ProducerTutorial.producer_id == current_user.id,
                ProducerTutorial.tutorial_type.in_(missing_types)
            )
        )
        created_tutorials = result.scalars().all()
        
        tutorials.extend(created_tutorials)
        tutorials.sort(key=lambda t: t.tutorial_type.value)
    
    completed_count = sum(1 for t in tutorials if t.status == TutorialStatus.COMPLETED)
    total_count = len(tutorials)
    completion_percentage = int((completed_count / total_count * 100)) if total_count > 0 else 0
    all_completed = completed_count == total_count

    return TutorialsSummaryResponse(
        show_tooltips=current_user.show_tooltips,
        tutorials=[TutorialResponse.model_validate(t) for t in tutorials],
        all_completed=all_completed,
        completion_percentage=completion_percentage,
    )


@router.get("/{tutorial_type}", response_model=TutorialResponse)
async def get_tutorial(
    tutorial_type: TutorialType,
    current_user: Annotated[User, Depends(get_current_verified_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TutorialResponse:
    """
    Get specific tutorial by type.

    Creates the tutorial record if it doesn't exist yet.
    """
    tutorial = await get_or_create_tutorial(db, current_user.id, tutorial_type)
    return TutorialResponse.model_validate(tutorial)


@router.patch("/{tutorial_type}/status", response_model=TutorialResponse)
async def update_tutorial_status(
    tutorial_type: TutorialType,
    status_update: TutorialStatusUpdate,
    current_user: Annotated[User, Depends(get_current_verified_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TutorialResponse:
    """
    Update tutorial status (complete, skip, etc).

    Automatically updates timestamps based on status:
    - IN_PROGRESS: sets started_at if not set
    - COMPLETED: sets completed_at
    - SKIPPED: marks as skipped
    """
    tutorial = await get_or_create_tutorial(db, current_user.id, tutorial_type)
    old_status = tutorial.status
    tutorial.status = status_update.status
    now = datetime.now(timezone.utc)

    if status_update.status == TutorialStatus.IN_PROGRESS and not tutorial.started_at:
        tutorial.started_at = now

    if status_update.status == TutorialStatus.COMPLETED:
        tutorial.completed_at = now
        if not tutorial.started_at:
            tutorial.started_at = now

    if old_status != status_update.status:
        tutorial.last_shown_at = now

    await db.commit()
    await db.refresh(tutorial)

    return TutorialResponse.model_validate(tutorial)


@router.post("/{tutorial_type}/show", response_model=TutorialResponse)
async def mark_tutorial_shown(
    tutorial_type: TutorialType,
    current_user: Annotated[User, Depends(get_current_verified_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TutorialResponse:
    """
    Mark tutorial as shown (update last_shown_at).

    Use this when displaying the tutorial to track when it was last shown.
    """
    tutorial = await get_or_create_tutorial(db, current_user.id, tutorial_type)

    tutorial.last_shown_at = datetime.now(timezone.utc)

    if tutorial.status == TutorialStatus.NOT_STARTED:
        tutorial.status = TutorialStatus.IN_PROGRESS
        if not tutorial.started_at:
            tutorial.started_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(tutorial)

    return TutorialResponse.model_validate(tutorial)


@router.post("/reset", response_model=TutorialsSummaryResponse)
async def reset_tutorials(
    reset_request: TutorialResetRequest,
    current_user: Annotated[User, Depends(get_current_verified_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TutorialsSummaryResponse:
    """
    Reset tutorial(s) to allow re-showing.

    If tutorial_type is specified, resets only that tutorial.
    If not specified, resets all tutorials.
    """
    if reset_request.tutorial_type:
        result = await db.execute(
            select(ProducerTutorial).where(
                ProducerTutorial.producer_id == current_user.id,
                ProducerTutorial.tutorial_type == reset_request.tutorial_type,
            )
        )
        tutorial = result.scalar_one_or_none()

        if tutorial:
            tutorial.status = TutorialStatus.NOT_STARTED
            tutorial.current_step = 0
            tutorial.started_at = None
            tutorial.completed_at = None
            tutorial.last_shown_at = None
            await db.commit()
    else:
        result = await db.execute(
            select(ProducerTutorial).where(
                ProducerTutorial.producer_id == current_user.id
            )
        )
        tutorials = result.scalars().all()

        for tutorial in tutorials:
            tutorial.status = TutorialStatus.NOT_STARTED
            tutorial.current_step = 0
            tutorial.started_at = None
            tutorial.completed_at = None
            tutorial.last_shown_at = None

        await db.commit()

    return await get_all_tutorials(current_user, db)


@router.post("/tooltips/toggle")
async def toggle_tooltips(
    toggle_request: TooltipsToggleRequest,
    current_user: Annotated[User, Depends(get_current_verified_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Toggle tooltips visibility globally.

    When set to False, the frontend should not show any tutorials/tooltips.
    """
    current_user.show_tooltips = toggle_request.show_tooltips

    await db.commit()

    return {
        "message": "Tooltips visibility updated",
        "show_tooltips": toggle_request.show_tooltips,
    }
