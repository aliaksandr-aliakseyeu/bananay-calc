"""Tags endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models.category import Tag
from app.schemas.tag import TagResponse

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("", response_model=list[TagResponse])
async def get_tags(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> list[Tag]:
    """
    Get all tags.

    Возвращает список всех тэгов (рубрик) для фильтрации точек доставки.
    Отсортировано по имени.
    """
    query = select(Tag).order_by(Tag.name)
    result = await db.execute(query)
    tags = result.scalars().all()
    return list(tags)
