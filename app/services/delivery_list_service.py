"""Service for managing user delivery lists."""
from typing import Tuple

from fastapi import HTTPException
from geoalchemy2 import functions as geo_func
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.config import settings
from app.db.models.delivery_list import DeliveryList, DeliveryListItem
from app.db.models.delivery_point import DeliveryPoint


class DeliveryListService:
    """Service for managing delivery lists."""

    @staticmethod
    async def get_user_lists(
        db: AsyncSession,
        user_id: int,
        with_items: bool = False,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None
    ) -> list[Tuple[DeliveryList, int]] | list[DeliveryList]:
        """
        Get all delivery lists for a user with item counts.

        Args:
            db: Database session
            user_id: User ID
            with_items: Load items with delivery points
            search: Search query for list name or description
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of tuples (DeliveryList, items_count) if with_items=False
            List of DeliveryList objects with preloaded items if with_items=True
        """
        if with_items:
            query = (
                select(DeliveryList)
                .where(DeliveryList.user_id == user_id)
                .options(
                    selectinload(DeliveryList.items).joinedload(DeliveryListItem.delivery_point)
                )
                .order_by(DeliveryList.is_default.desc(), DeliveryList.created_at.desc())
            )
            
            if search:
                search_filter = f"%{search}%"
                query = query.where(
                    (DeliveryList.name.ilike(search_filter)) |
                    (DeliveryList.description.ilike(search_filter))
                )
            
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)
            
            result = await db.execute(query)
            return result.scalars().all()
        else:
            query = (
                select(
                    DeliveryList,
                    func.count(DeliveryListItem.id).label("items_count")
                )
                .outerjoin(DeliveryListItem, DeliveryList.id == DeliveryListItem.list_id)
                .where(DeliveryList.user_id == user_id)
                .group_by(DeliveryList.id)
                .order_by(DeliveryList.is_default.desc(), DeliveryList.created_at.desc())
            )
            
            if search:
                search_filter = f"%{search}%"
                query = query.where(
                    (DeliveryList.name.ilike(search_filter)) |
                    (DeliveryList.description.ilike(search_filter))
                )
            
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)
            
            result = await db.execute(query)
            return result.all()
    
    @staticmethod
    async def count_user_lists(
        db: AsyncSession,
        user_id: int,
        search: str | None = None
    ) -> int:
        """
        Count total delivery lists for a user.

        Args:
            db: Database session
            user_id: User ID
            search: Search query for list name or description

        Returns:
            Total count of lists
        """
        query = select(func.count(DeliveryList.id)).where(DeliveryList.user_id == user_id)
        
        if search:
            search_filter = f"%{search}%"
            query = query.where(
                (DeliveryList.name.ilike(search_filter)) |
                (DeliveryList.description.ilike(search_filter))
            )
        
        result = await db.execute(query)
        return result.scalar_one()

    @staticmethod
    async def get_list_by_id(
        db: AsyncSession,
        list_id: int,
        user_id: int,
        with_items: bool = False
    ) -> DeliveryList | None:
        """
        Get delivery list by ID.

        Args:
            db: Database session
            list_id: List ID
            user_id: User ID
            with_items: Load items with delivery points

        Returns:
            DeliveryList or None if not found
        """
        query = select(DeliveryList).where(
            DeliveryList.id == list_id,
            DeliveryList.user_id == user_id
        )

        if with_items:
            query = query.options(
                selectinload(DeliveryList.items).joinedload(DeliveryListItem.delivery_point)
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_list(
        db: AsyncSession,
        user_id: int,
        name: str,
        description: str | None = None,
        is_default: bool = False
    ) -> DeliveryList:
        """
        Create a new delivery list.

        Args:
            db: Database session
            user_id: User ID
            name: List name
            description: List description
            is_default: Set as default list

        Returns:
            Created DeliveryList

        Raises:
            HTTPException: If limit exceeded or validation fails
        """
        count_query = select(func.count(DeliveryList.id)).where(DeliveryList.user_id == user_id)
        result = await db.execute(count_query)
        count = result.scalar_one()

        if count >= settings.MAX_DELIVERY_LISTS_PER_USER:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum delivery lists limit reached ({settings.MAX_DELIVERY_LISTS_PER_USER})"
            )

        duplicate_query = select(DeliveryList).where(
            DeliveryList.user_id == user_id,
            DeliveryList.name == name
        )
        result = await db.execute(duplicate_query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"List with name '{name}' already exists"
            )

        if count == 0:
            is_default = True

        if is_default:
            update_query = select(DeliveryList).where(
                DeliveryList.user_id == user_id,
                DeliveryList.is_default
            )
            result = await db.execute(update_query)
            for existing_list in result.scalars():
                existing_list.is_default = False

        new_list = DeliveryList(
            user_id=user_id,
            name=name,
            description=description,
            is_default=is_default
        )
        db.add(new_list)
        await db.commit()
        await db.refresh(new_list)
        return new_list

    @staticmethod
    async def update_list(
        db: AsyncSession,
        delivery_list: DeliveryList,
        name: str | None = None,
        description: str | None = None,
        is_default: bool | None = None
    ) -> DeliveryList:
        """
        Update delivery list.

        Args:
            db: Database session
            delivery_list: DeliveryList to update
            name: New name
            description: New description
            is_default: New default status

        Returns:
            Updated DeliveryList
        """
        if name is not None:
            duplicate_query = select(DeliveryList).where(
                DeliveryList.user_id == delivery_list.user_id,
                DeliveryList.name == name,
                DeliveryList.id != delivery_list.id
            )
            result = await db.execute(duplicate_query)
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail=f"List with name '{name}' already exists"
                )
            delivery_list.name = name

        if description is not None:
            delivery_list.description = description

        if is_default is not None and is_default != delivery_list.is_default:
            if is_default:
                update_query = select(DeliveryList).where(
                    DeliveryList.user_id == delivery_list.user_id,
                    DeliveryList.is_default,
                    DeliveryList.id != delivery_list.id
                )
                result = await db.execute(update_query)
                for existing_list in result.scalars():
                    existing_list.is_default = False

            delivery_list.is_default = is_default

        await db.commit()
        await db.refresh(delivery_list)
        return delivery_list

    @staticmethod
    async def delete_list(db: AsyncSession, delivery_list: DeliveryList) -> None:
        """
        Delete delivery list (cascade deletes items).

        Args:
            db: Database session
            delivery_list: DeliveryList to delete
        """
        await db.delete(delivery_list)
        await db.commit()

    @staticmethod
    async def add_point_to_list(
        db: AsyncSession,
        list_id: int,
        delivery_point_id: int,
        custom_name: str | None = None,
        notes: str | None = None
    ) -> DeliveryListItem:
        """
        Add a delivery point to a list.

        Args:
            db: Database session
            list_id: List ID
            delivery_point_id: Delivery point ID
            custom_name: Custom name
            notes: Notes

        Returns:
            Created DeliveryListItem

        Raises:
            HTTPException: If limit exceeded or validation fails
        """
        count_query = select(func.count(DeliveryListItem.id)).where(
            DeliveryListItem.list_id == list_id
        )
        result = await db.execute(count_query)
        count = result.scalar_one()

        if count >= settings.MAX_ITEMS_PER_LIST:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum items per list limit reached ({settings.MAX_ITEMS_PER_LIST})"
            )

        point_query = select(DeliveryPoint).where(DeliveryPoint.id == delivery_point_id)
        result = await db.execute(point_query)
        point = result.scalar_one_or_none()
        if not point:
            raise HTTPException(status_code=404, detail="Delivery point not found")

        duplicate_query = select(DeliveryListItem).where(
            DeliveryListItem.list_id == list_id,
            DeliveryListItem.delivery_point_id == delivery_point_id
        )
        result = await db.execute(duplicate_query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Point already in this list"
            )

        item = DeliveryListItem(
            list_id=list_id,
            delivery_point_id=delivery_point_id,
            custom_name=custom_name,
            notes=notes
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)

        await db.refresh(item, ["delivery_point"])
        return item

    @staticmethod
    async def get_item_by_id(
        db: AsyncSession,
        item_id: int,
        list_id: int
    ) -> DeliveryListItem | None:
        """Get list item by ID."""
        query = select(DeliveryListItem).where(
            DeliveryListItem.id == item_id,
            DeliveryListItem.list_id == list_id
        ).options(joinedload(DeliveryListItem.delivery_point))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_item(
        db: AsyncSession,
        item: DeliveryListItem,
        custom_name: str | None = None,
        notes: str | None = None
    ) -> DeliveryListItem:
        """Update list item."""
        if custom_name is not None:
            item.custom_name = custom_name
        if notes is not None:
            item.notes = notes

        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def delete_item(db: AsyncSession, item: DeliveryListItem) -> None:
        """Delete list item."""
        await db.delete(item)
        await db.commit()

    @staticmethod
    async def check_point_in_list(
        db: AsyncSession,
        list_id: int,
        delivery_point_id: int
    ) -> Tuple[bool, int | None]:
        """
        Check if a delivery point is in the list.

        Returns:
            Tuple of (in_list: bool, item_id: int | None)
        """
        query = select(DeliveryListItem).where(
            DeliveryListItem.list_id == list_id,
            DeliveryListItem.delivery_point_id == delivery_point_id
        )
        result = await db.execute(query)
        item = result.scalar_one_or_none()

        if item:
            return True, item.id
        return False, None

    @staticmethod
    async def toggle_point(
        db: AsyncSession,
        list_id: int,
        delivery_point_id: int
    ) -> Tuple[str, int | None]:
        """
        Toggle point in list (add if not exists, remove if exists).

        Returns:
            Tuple of (action: "added" | "removed", item_id: int | None)
        """
        in_list, item_id = await DeliveryListService.check_point_in_list(
            db, list_id, delivery_point_id
        )

        if in_list and item_id:
            item_query = select(DeliveryListItem).where(DeliveryListItem.id == item_id)
            result = await db.execute(item_query)
            item = result.scalar_one()
            await db.delete(item)
            await db.commit()
            return "removed", None
        else:
            item = await DeliveryListService.add_point_to_list(
                db, list_id, delivery_point_id
            )
            return "added", item.id

    @staticmethod
    async def find_points_in_radius(
        db: AsyncSession,
        lat: float,
        lon: float,
        radius_meters: int = settings.DEFAULT_SEARCH_RADIUS_METERS
    ) -> list[Tuple[DeliveryPoint, float]]:
        """
        Find delivery points within a radius from coordinates.

        Args:
            db: Database session
            lat: Latitude
            lon: Longitude
            radius_meters: Search radius in meters (default from config)

        Returns:
            List of tuples (DeliveryPoint, distance_in_meters)
        """
        if radius_meters > settings.MAX_SEARCH_RADIUS_METERS:
            radius_meters = settings.MAX_SEARCH_RADIUS_METERS

        point = geo_func.ST_SetSRID(geo_func.ST_MakePoint(lon, lat), 4326)

        query = select(
            DeliveryPoint,
            geo_func.ST_Distance(
                geo_func.ST_Transform(DeliveryPoint.location, 3857),
                geo_func.ST_Transform(point, 3857)
            ).label("distance")
        ).where(
            geo_func.ST_DWithin(
                geo_func.ST_Transform(DeliveryPoint.location, 3857),
                geo_func.ST_Transform(point, 3857),
                radius_meters
            ),
            DeliveryPoint.is_active
        ).order_by("distance")

        result = await db.execute(query)
        return result.all()
