"""Service layer for delivery templates."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.delivery_template import (DeliveryTemplate,
                                             DeliveryTemplatePoint)
from app.db.models.producer_sku import ProducerSKU
from app.schemas.calculator import ProductParams
from app.services.calculator_service import CalculatorService


class DeliveryTemplateService:
    """Service for managing delivery templates."""

    @staticmethod
    async def get_user_templates(
        db: AsyncSession,
        user_id: int,
        with_points: bool = False,
        only_active: bool = True,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[DeliveryTemplate]:
        """Get templates for a user with optional search and pagination."""
        query = select(DeliveryTemplate).where(DeliveryTemplate.producer_id == user_id)

        if only_active:
            query = query.where(DeliveryTemplate.is_active)

        if search and search.strip():
            search_filter = f"%{search.strip()}%"
            query = query.where(
                (DeliveryTemplate.name.ilike(search_filter))
                | (DeliveryTemplate.description.ilike(search_filter))
            )

        if with_points:
            query = query.options(
                selectinload(DeliveryTemplate.points).selectinload(
                    DeliveryTemplatePoint.delivery_point
                )
            )

        query = query.order_by(
            DeliveryTemplate.last_used_at.desc().nulls_last(),
            DeliveryTemplate.created_at.desc()
        )

        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count_user_templates(
        db: AsyncSession,
        user_id: int,
        only_active: bool = True,
        search: str | None = None,
    ) -> int:
        """Count templates for a user (with optional search filter)."""
        query = select(func.count(DeliveryTemplate.id)).where(
            DeliveryTemplate.producer_id == user_id
        )
        if only_active:
            query = query.where(DeliveryTemplate.is_active)
        if search and search.strip():
            search_filter = f"%{search.strip()}%"
            query = query.where(
                (DeliveryTemplate.name.ilike(search_filter))
                | (DeliveryTemplate.description.ilike(search_filter))
            )
        result = await db.execute(query)
        return result.scalar_one() or 0

    @staticmethod
    async def get_template_by_id(
        db: AsyncSession,
        template_id: int,
        user_id: int,
        with_points: bool = False,
    ) -> DeliveryTemplate | None:
        """Get template by ID (with ownership check)."""
        query = select(DeliveryTemplate).where(
            DeliveryTemplate.id == template_id,
            DeliveryTemplate.producer_id == user_id,
        )

        if with_points:
            query = query.options(
                selectinload(DeliveryTemplate.points).selectinload(
                    DeliveryTemplatePoint.delivery_point
                )
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_template(
        db: AsyncSession,
        user_id: int,
        name: str,
        producer_sku_id: int,
        region_id: int,
        warehouse_lat: float,
        warehouse_lon: float,
        description: str | None = None,
    ) -> DeliveryTemplate:
        """Create a new template."""
        sku_result = await db.execute(
            select(ProducerSKU).where(
                ProducerSKU.id == producer_sku_id,
                ProducerSKU.producer_id == user_id,
            )
        )
        sku = sku_result.scalar_one_or_none()
        if not sku:
            raise ValueError("Producer SKU not found or doesn't belong to user")

        template = DeliveryTemplate(
            producer_id=user_id,
            name=name,
            description=description,
            producer_sku_id=producer_sku_id,
            region_id=region_id,
            warehouse_lat=warehouse_lat,
            warehouse_lon=warehouse_lon,
            total_quantity=0,
            usage_count=0,
            is_active=True,
        )

        db.add(template)
        await db.commit()
        await db.refresh(template)

        return template

    @staticmethod
    async def update_template(
        db: AsyncSession,
        template: DeliveryTemplate,
        name: str | None = None,
        description: str | None = None,
        warehouse_lat: float | None = None,
        warehouse_lon: float | None = None,
        is_active: bool | None = None,
    ) -> DeliveryTemplate:
        """Update template."""
        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if warehouse_lat is not None:
            template.warehouse_lat = warehouse_lat
        if warehouse_lon is not None:
            template.warehouse_lon = warehouse_lon
        if is_active is not None:
            template.is_active = is_active

        await db.commit()
        await db.refresh(template)

        return template

    @staticmethod
    async def delete_template(db: AsyncSession, template: DeliveryTemplate) -> None:
        """Delete template (or archive it)."""
        template.is_active = False
        await db.commit()

    @staticmethod
    async def add_point_to_template(
        db: AsyncSession,
        template_id: int,
        delivery_point_id: int,
        quantity: int,
        notes: str | None = None,
    ) -> DeliveryTemplatePoint:
        """Add a delivery point to template."""
        existing = await db.execute(
            select(DeliveryTemplatePoint).where(
                DeliveryTemplatePoint.template_id == template_id,
                DeliveryTemplatePoint.delivery_point_id == delivery_point_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Point already exists in this template")

        point = DeliveryTemplatePoint(
            template_id=template_id,
            delivery_point_id=delivery_point_id,
            quantity=quantity,
            notes=notes,
        )

        db.add(point)

        template = await db.get(DeliveryTemplate, template_id)
        if template:
            template.total_quantity += quantity

        await db.commit()
        await db.refresh(point)

        return point

    @staticmethod
    async def update_template_point(
        db: AsyncSession,
        point: DeliveryTemplatePoint,
        quantity: int | None = None,
        notes: str | None = None,
    ) -> DeliveryTemplatePoint:
        """Update a template point."""
        old_quantity = point.quantity

        if quantity is not None:
            point.quantity = quantity
        if notes is not None:
            point.notes = notes

        if quantity is not None and quantity != old_quantity:
            template = await db.get(DeliveryTemplate, point.template_id)
            if template:
                template.total_quantity = template.total_quantity - old_quantity + quantity

        await db.commit()
        await db.refresh(point)

        return point

    @staticmethod
    async def delete_template_point(
        db: AsyncSession,
        point: DeliveryTemplatePoint,
    ) -> None:
        """Remove a point from template."""
        template_id = point.template_id
        quantity = point.quantity

        await db.delete(point)

        template = await db.get(DeliveryTemplate, template_id)
        if template:
            template.total_quantity -= quantity

        await db.commit()

    @staticmethod
    async def get_template_point_by_id(
        db: AsyncSession,
        point_id: int,
        template_id: int,
    ) -> DeliveryTemplatePoint | None:
        """Get template point by ID."""
        result = await db.execute(
            select(DeliveryTemplatePoint).where(
                DeliveryTemplatePoint.id == point_id,
                DeliveryTemplatePoint.template_id == template_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def sync_template_points(
        db: AsyncSession,
        template_id: int,
        points_data: list[dict],
    ) -> int:
        """
        Sync template points in batch.
        
        For each point in points_data:
        - If point already exists: update quantity
        - If point doesn't exist: create new
        
        Returns: number of points processed
        """
        result = await db.execute(
            select(DeliveryTemplatePoint).where(
                DeliveryTemplatePoint.template_id == template_id
            )
        )
        existing_points = result.scalars().all()
        existing_map = {p.delivery_point_id: p for p in existing_points}
        
        template = await db.get(DeliveryTemplate, template_id)
        if not template:
            raise ValueError("Template not found")
        
        total_quantity_change = 0
        processed_count = 0
        
        for point_data in points_data:
            delivery_point_id = point_data['delivery_point_id']
            new_quantity = point_data['quantity']
            notes = point_data.get('notes')
            
            if delivery_point_id in existing_map:
                existing_point = existing_map[delivery_point_id]
                old_quantity = existing_point.quantity
                existing_point.quantity = new_quantity
                if notes is not None:
                    existing_point.notes = notes
                total_quantity_change += (new_quantity - old_quantity)
            else:
                new_point = DeliveryTemplatePoint(
                    template_id=template_id,
                    delivery_point_id=delivery_point_id,
                    quantity=new_quantity,
                    notes=notes,
                )
                db.add(new_point)
                total_quantity_change += new_quantity
            
            processed_count += 1
        
        template.total_quantity += total_quantity_change
        
        await db.commit()
        
        return processed_count

    @staticmethod
    async def calculate_template_cost(
        db: AsyncSession,
        template: DeliveryTemplate,
    ) -> dict:
        """Calculate delivery cost for a template."""
        await db.refresh(template, ["points", "producer_sku"])

        if not template.points:
            raise ValueError("Template has no delivery points")

        sku = template.producer_sku
        if not sku.items_per_box or sku.items_per_box <= 0:
            raise ValueError("SKU must have items_per_box configured")

        product_params = ProductParams(
            length_cm=int(sku.length_cm),
            width_cm=int(sku.width_cm),
            height_cm=int(sku.height_cm),
            weight_kg=sku.weight_kg,
            items_per_box=sku.items_per_box,
        )

        point_quantities = [
            (point.delivery_point_id, point.quantity)
            for point in template.points
        ]

        calculator = CalculatorService(db)
        calc_result = await calculator.calculate_by_points(
            region_id=template.region_id,
            supplier_lat=template.warehouse_lat,
            supplier_lon=template.warehouse_lon,
            product=product_params,
            point_quantities=point_quantities,
        )

        template.estimated_cost = Decimal(str(calc_result["cost_per_item"] * calc_result["total_quantity"]))
        template.cost_per_unit = Decimal(str(calc_result["cost_per_item"]))
        template.last_calculated_at = datetime.now(timezone.utc)

        await db.commit()

        return {
            "total_quantity": calc_result["total_quantity"],
            "estimated_cost": float(template.estimated_cost),
            "cost_per_unit": float(template.cost_per_unit),
            "calculation_details": calc_result,
        }

    @staticmethod
    async def get_template_usage_history(
        db: AsyncSession,
        template_id: int,
        user_id: int,
    ) -> dict:
        """Get usage history for a template."""
        template = await DeliveryTemplateService.get_template_by_id(
            db, template_id, user_id
        )
        if not template:
            raise ValueError("Template not found")

        from app.db.models.delivery_order import (DeliveryOrder,
                                                  DeliveryOrderItem)

        result = await db.execute(
            select(DeliveryOrderItem, DeliveryOrder)
            .join(DeliveryOrder, DeliveryOrderItem.order_id == DeliveryOrder.id)
            .where(DeliveryOrderItem.template_id == template_id)
            .order_by(DeliveryOrder.created_at.desc())
            .limit(50)
        )

        orders = []
        for item, order in result.all():
            orders.append({
                "order_id": order.id,
                "order_number": order.order_number,
                "created_at": order.created_at.isoformat(),
                "status": order.status.value,
            })

        return {
            "template_id": template.id,
            "template_name": template.name,
            "usage_count": template.usage_count,
            "last_used_at": template.last_used_at,
            "orders": orders,
        }

    @staticmethod
    async def increment_usage_count(
        db: AsyncSession,
        template_id: int,
    ) -> None:
        """Increment template usage count and update last_used_at."""
        template = await db.get(DeliveryTemplate, template_id)
        if template:
            template.usage_count += 1
            template.last_used_at = datetime.now(timezone.utc)
            await db.commit()
