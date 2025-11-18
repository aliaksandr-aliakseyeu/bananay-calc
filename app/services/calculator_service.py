"""Calculator service for delivery cost calculations."""
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.delivery_point import DeliveryPoint
from app.db.models.distribution_center import DistributionCenter
from app.db.models.region_pricing import RegionPricing
from app.db.models.sector import Sector
from app.schemas.calculator import ProductParams
from app.services.distance_service import DistanceService

logger = logging.getLogger(__name__)


class CalculatorService:
    """Service for delivery cost calculations."""

    def __init__(self, db: AsyncSession):
        """Initialize calculator service."""
        self.db = db
        self.distance_service = DistanceService()

    async def get_region_pricing(self, region_id: int) -> RegionPricing | None:
        """Get pricing configuration for region."""
        result = await self.db.execute(
            select(RegionPricing).where(RegionPricing.region_id == region_id)
        )
        return result.scalar_one_or_none()

    async def get_nearest_distribution_center(
        self,
        supplier_lat: float,
        supplier_lon: float,
        region_id: int,
    ) -> tuple[DistributionCenter, float, str] | None:
        """
        Find nearest distribution center to supplier location.

        Args:
            supplier_lat: Supplier latitude
            supplier_lon: Supplier longitude
            region_id: Region ID

        Returns:
            Tuple of (distribution_center, distance_km, calculation_method) or None
        """
        result = await self.db.execute(
            select(DistributionCenter).where(
                DistributionCenter.is_active == True  # noqa: E712
            )
        )
        distribution_centers = result.scalars().all()

        if not distribution_centers:
            logger.warning("No distribution centers found")
            return None

        dc_distances: list[tuple[DistributionCenter, float]] = []

        for dc in distribution_centers:
            dc_lat, dc_lon = self.distance_service.extract_coordinates(dc.location)
            straight_distance = self.distance_service.haversine_distance(
                supplier_lat, supplier_lon, dc_lat, dc_lon
            )
            dc_distances.append((dc, straight_distance))

        dc_distances.sort(key=lambda x: x[1])
        top_3_dcs = dc_distances[:3]

        dc_route_distances: list[tuple[DistributionCenter, float, str]] = []

        for dc, straight_distance in top_3_dcs:
            dc_lat, dc_lon = self.distance_service.extract_coordinates(dc.location)

            route_distance, method = await self.distance_service.calculate_distance_with_fallback(
                supplier_lat, supplier_lon, dc_lat, dc_lon
            )

            dc_route_distances.append((dc, route_distance, method))

        nearest_dc, distance_km, method = min(
            dc_route_distances, key=lambda x: x[1]
        )

        logger.info(
            "Selected nearest DC: %s (distance: %.2f km, method: %s)",
            nearest_dc.name,
            distance_km,
            method
        )

        return nearest_dc, distance_km, method

    async def get_delivery_info_from_points(
        self,
        delivery_point_ids: list[int],
        region_id: int,
    ) -> tuple[int, int, int]:
        """
        Get delivery information from delivery point IDs.

        Uses PostGIS spatial query to check if delivery points fall within sector boundaries.

        Args:
            delivery_point_ids: List of delivery point IDs
            region_id: Region ID for validation

        Returns:
            Tuple of (num_valid_points, num_sectors, num_ignored_points)
        """
        result = await self.db.execute(
            select(DeliveryPoint, Sector)
            .join(
                Sector,
                func.ST_Within(DeliveryPoint.location, Sector.boundary)
            )
            .where(
                DeliveryPoint.id.in_(delivery_point_ids),
                DeliveryPoint.is_active == True,  # noqa: E712
                Sector.region_id == region_id
            )
        )

        valid_points = result.all()

        unique_point_ids = set(point.DeliveryPoint.id for point in valid_points)
        num_valid_points = len(unique_point_ids)
        num_ignored = len(delivery_point_ids) - num_valid_points
        unique_sectors = set(point.Sector.id for point in valid_points)
        num_sectors = len(unique_sectors)

        logger.info(
            "Delivery points: %d valid (from %d point-sector matches), %d ignored, %d sectors",
            num_valid_points,
            len(valid_points),
            num_ignored,
            num_sectors
        )

        return num_valid_points, num_sectors, num_ignored

    async def get_max_sectors_for_region(self, region_id: int) -> int:
        """Get total number of sectors for region."""
        result = await self.db.execute(
            select(func.count(Sector.id)).where(Sector.region_id == region_id)
        )
        count = result.scalar()
        return count or 0

    def calculate_delivery_costs(
        self,
        pricing: RegionPricing,
        distance_km: float,
        num_points: int,
        num_sectors: int,
    ) -> dict[str, Any]:
        """
        Calculate all delivery costs.

        Args:
            pricing: Region pricing configuration
            distance_km: Distance to distribution center
            num_points: Number of delivery points
            num_sectors: Number of sectors

        Returns:
            Dictionary with all cost calculations
        """
        driver_cost = pricing.planned_work_hours * pricing.driver_hourly_rate
        company_revenue = pricing.service_fee_per_kg * pricing.standard_trip_weight
        fuel_liters = (
            pricing.fuel_consumption_per_100km / Decimal("100")
        ) * (Decimal(str(distance_km)) * Decimal("2"))
        fuel_cost = fuel_liters * pricing.fuel_price_per_liter
        transport_cost = fuel_cost * pricing.depreciation_coefficient
        warehouse_cost = (
            pricing.warehouse_processing_per_kg * pricing.standard_trip_weight
        )
        if num_points < pricing.min_points_for_discount:
            delivery_cost = (
                num_sectors
                * pricing.delivery_point_cost
                * pricing.min_points_for_discount
            )
        else:
            discount_steps = int(
                (num_points - pricing.min_points_for_discount)
                / pricing.discount_step_points
            )
            discount_percent = (
                pricing.initial_discount_percent
                + discount_steps * pricing.discount_step_percent
            )

            base_cost = (
                num_sectors
                * pricing.delivery_point_cost
                * pricing.min_points_for_discount
            )
            delivery_cost = base_cost * (Decimal("1") - discount_percent / Decimal("100"))
        total_trip_cost = (
            driver_cost
            + company_revenue
            + transport_cost
            + warehouse_cost
            + delivery_cost
        )

        num_standard_boxes = (
            pricing.standard_trip_weight / pricing.standard_box_max_weight
        )
        standard_box_cost = total_trip_cost / num_standard_boxes

        return {
            "driver_cost": driver_cost,
            "company_revenue": company_revenue,
            "fuel_cost": fuel_cost,
            "transport_cost": transport_cost,
            "warehouse_cost": warehouse_cost,
            "delivery_cost": delivery_cost,
            "total_trip_cost": total_trip_cost,
            "num_standard_boxes": num_standard_boxes,
            "standard_box_cost": standard_box_cost,
        }

    def calculate_product_fitting(
        self,
        pricing: RegionPricing,
        product: ProductParams,
    ) -> dict[str, Any]:
        """
        Calculate how many items fit in standard box.

        Args:
            pricing: Region pricing configuration
            product: Product parameters

        Returns:
            Dictionary with fitting calculations
        """
        n_length = pricing.standard_box_length // product.length_cm
        n_width = pricing.standard_box_width // product.width_cm
        n_height = pricing.standard_box_height // product.height_cm
        items_by_dimensions = n_length * n_width * n_height
        items_by_weight = int(
            pricing.standard_box_max_weight / product.weight_kg
        )
        items_in_standard_box = min(items_by_dimensions, items_by_weight)

        logger.info(
            "Product fitting: by_dimensions=%d, by_weight=%d, final=%d",
            items_by_dimensions,
            items_by_weight,
            items_in_standard_box
        )

        return {
            "items_by_dimensions": items_by_dimensions,
            "items_by_weight": items_by_weight,
            "items_in_standard_box": items_in_standard_box,
        }

    def calculate_final_results(
        self,
        standard_box_cost: Decimal,
        items_in_standard_box: int,
        items_per_supplier_box: int,
    ) -> dict[str, Decimal]:
        """
        Calculate final delivery costs for supplier's product.

        Args:
            standard_box_cost: Cost of delivering one standard box
            items_in_standard_box: How many items fit in standard box
            items_per_supplier_box: Items per supplier's box

        Returns:
            Dictionary with final costs (rounded to 2 decimals)
        """
        cost_per_item = standard_box_cost / Decimal(str(items_in_standard_box))
        cost_per_supplier_box = cost_per_item * Decimal(str(items_per_supplier_box))
        cost_per_item = cost_per_item.quantize(Decimal("0.01"))
        cost_per_supplier_box = cost_per_supplier_box.quantize(Decimal("0.01"))

        return {
            "cost_per_item": cost_per_item,
            "cost_per_supplier_box": cost_per_supplier_box,
        }

    async def calculate_by_points(
        self,
        region_id: int,
        supplier_lat: float,
        supplier_lon: float,
        product: ProductParams,
        delivery_point_ids: list[int],
    ) -> dict[str, Any]:
        """
        Calculate delivery costs using specific delivery points.

        Args:
            region_id: Region ID
            supplier_lat: Supplier latitude
            supplier_lon: Supplier longitude
            product: Product parameters
            delivery_point_ids: List of delivery point IDs

        Returns:
            Dictionary with calculation results

        Raises:
            ValueError: If validation fails
        """
        pricing = await self.get_region_pricing(region_id)
        if not pricing:
            raise ValueError(f"Pricing not configured for region {region_id}")
        num_points, num_sectors, num_ignored = await self.get_delivery_info_from_points(
            delivery_point_ids, region_id
        )

        if num_points == 0:
            raise ValueError("No valid delivery points provided")
        dc_info = await self.get_nearest_distribution_center(
            supplier_lat, supplier_lon, region_id
        )
        if not dc_info:
            raise ValueError("No distribution centers found")

        dc, distance_km, distance_method = dc_info
        costs = self.calculate_delivery_costs(
            pricing, distance_km, num_points, num_sectors
        )
        fitting = self.calculate_product_fitting(pricing, product)

        if fitting["items_in_standard_box"] == 0:
            raise ValueError("Product doesn't fit in standard box")
        final = self.calculate_final_results(
            costs["standard_box_cost"],
            fitting["items_in_standard_box"],
            product.items_per_box,
        )

        return {
            "items_in_standard_box": fitting["items_in_standard_box"],
            "cost_per_item": final["cost_per_item"],
            "cost_per_supplier_box": final["cost_per_supplier_box"],
            "delivery_points_used": num_points,
            "delivery_points_ignored": num_ignored,
            "sectors_count": num_sectors,
            "distance_to_dc_km": Decimal(str(distance_km)).quantize(Decimal("0.01")),
            "nearest_dc_name": dc.name,
        }

    async def calculate_estimate(
        self,
        region_id: int,
        supplier_lat: float,
        supplier_lon: float,
        product: ProductParams,
        num_points: int,
        num_sectors: int | None = None,
    ) -> dict[str, Any]:
        """
        Calculate delivery costs using estimated numbers.

        Args:
            region_id: Region ID
            supplier_lat: Supplier latitude
            supplier_lon: Supplier longitude
            product: Product parameters
            num_points: Number of delivery points
            num_sectors: Number of sectors (optional)

        Returns:
            Dictionary with calculation results

        Raises:
            ValueError: If validation fails
        """
        pricing = await self.get_region_pricing(region_id)
        if not pricing:
            raise ValueError(f"Pricing not configured for region {region_id}")
        if num_sectors is None:
            num_sectors = await self.get_max_sectors_for_region(region_id)
            logger.info("Using max sectors for region: %d", num_sectors)
        dc_info = await self.get_nearest_distribution_center(
            supplier_lat, supplier_lon, region_id
        )
        if not dc_info:
            raise ValueError("No distribution centers found")

        dc, distance_km, distance_method = dc_info
        costs = self.calculate_delivery_costs(
            pricing, distance_km, num_points, num_sectors
        )
        fitting = self.calculate_product_fitting(pricing, product)

        if fitting["items_in_standard_box"] == 0:
            raise ValueError("Product doesn't fit in standard box")
        final = self.calculate_final_results(
            costs["standard_box_cost"],
            fitting["items_in_standard_box"],
            product.items_per_box,
        )

        return {
            "items_in_standard_box": fitting["items_in_standard_box"],
            "cost_per_item": final["cost_per_item"],
            "cost_per_supplier_box": final["cost_per_supplier_box"],
            "distance_to_dc_km": Decimal(str(distance_km)).quantize(Decimal("0.01")),
            "nearest_dc_name": dc.name,
        }
