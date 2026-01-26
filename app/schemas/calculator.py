"""Calculator schemas."""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SupplierLocation(BaseModel):
    """Supplier location coordinates."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude", examples=[43.585472])
    longitude: float = Field(..., ge=-180, le=180, description="Longitude", examples=[39.723098])


class DeliveryPointQuantity(BaseModel):
    """Delivery point with quantity."""

    point_id: int = Field(..., gt=0, description="Delivery point ID", examples=[123])
    quantity: int = Field(..., gt=0, description="Quantity for this delivery point", examples=[5])


class ProductParams(BaseModel):
    """Product parameters."""

    length_cm: int = Field(..., gt=0, description="Product length, cm", examples=[20])
    width_cm: int = Field(..., gt=0, description="Product width, cm", examples=[10])
    height_cm: int = Field(..., gt=0, description="Product height, cm", examples=[10])
    weight_kg: Decimal = Field(..., gt=0, description="Weight of one item, kg", examples=[1.0])
    items_per_box: int = Field(
        ..., gt=0, description="Number of items in supplier's box", examples=[15]
    )


class DeliveryParams(BaseModel):
    """Delivery parameters for estimate calculation."""

    num_points: int = Field(..., gt=0, description="Number of delivery points", examples=[300])
    num_sectors: int | None = Field(
        None, gt=0, description="Number of sectors (optional)", examples=[10]
    )


class CalculatorByPointsRequest(BaseModel):
    """Request for calculator by delivery points."""

    region_id: int = Field(..., description="Region ID", examples=[1])
    supplier_location: SupplierLocation = Field(..., description="Supplier coordinates")
    product: ProductParams = Field(..., description="Product parameters")
    point_quantities: list[DeliveryPointQuantity] = Field(
        ..., min_length=1, description="List of delivery points with quantities"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "region_id": 1,
                "supplier_location": {
                    "latitude": 43.653366116451195,
                    "longitude": 39.64989059534503
                },
                "product": {
                    "length_cm": 20,
                    "width_cm": 10,
                    "height_cm": 10,
                    "weight_kg": 1,
                    "items_per_box": 15
                },
                "point_quantities": [
                    {"point_id": 4510, "quantity": 5},
                    {"point_id": 328, "quantity": 3},
                    {"point_id": 1299, "quantity": 10},
                    {"point_id": 4877, "quantity": 2},
                    {"point_id": 2590, "quantity": 7}
                ]
            }
        }
    )


class CalculatorEstimateRequest(BaseModel):
    """Request for calculator estimate."""

    region_id: int = Field(..., description="Region ID", examples=[1])
    supplier_location: SupplierLocation = Field(..., description="Supplier coordinates")
    product: ProductParams = Field(..., description="Product parameters")
    delivery: DeliveryParams = Field(..., description="Delivery parameters")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "region_id": 1,
                "supplier_location": {
                    "latitude": 43.653366116451195,
                    "longitude": 39.64989059534503
                },
                "product": {
                    "length_cm": 20,
                    "width_cm": 10,
                    "height_cm": 10,
                    "weight_kg": 1,
                    "items_per_box": 15
                },
                "delivery": {
                    "num_points": 300,
                    "num_sectors": 10
                }
            }
        }
    )


class CalculatorByPointsResponse(BaseModel):
    """Response for calculator by delivery points."""

    items_in_standard_box: int = Field(
        ...,
        description="Number of supplier's items in one standard box "
        "considering weight limit",
        examples=[18],
    )
    cost_per_item: Decimal = Field(
        ...,
        description="Delivery cost per one supplier's item, RUB",
        examples=[38.29],
    )
    cost_per_supplier_box: Decimal = Field(
        ...,
        description="Delivery cost per one supplier's box, RUB",
        examples=[574.35],
    )
    total_quantity: int = Field(
        ..., description="Total quantity across all delivery points", examples=[150]
    )
    delivery_points_ignored: int = Field(
        ..., description="Number of ignored delivery points", examples=[5]
    )
    regions_count: int = Field(
        ...,
        description="Number of unique regions containing delivery points",
        examples=[3],
    )
    distance_to_dc_km: Decimal = Field(
        ...,
        description="Distance to nearest distribution center, km",
        examples=[15.50],
    )
    nearest_dc_name: str = Field(
        ...,
        description="Name of nearest distribution center",
        examples=["РЦ Сочи"],
    )


class CalculatorEstimateResponse(BaseModel):
    """Response for calculator estimate."""

    items_in_standard_box: int = Field(
        ...,
        description="Number of supplier's items in one standard box "
        "considering weight limit",
        examples=[18],
    )
    cost_per_item: Decimal = Field(
        ...,
        description="Delivery cost per one supplier's item, RUB",
        examples=[38.29],
    )
    cost_per_supplier_box: Decimal = Field(
        ...,
        description="Delivery cost per one supplier's box, RUB",
        examples=[574.35],
    )
    distance_to_dc_km: Decimal = Field(
        ...,
        description="Distance to nearest distribution center, km",
        examples=[15.50],
    )
    nearest_dc_name: str = Field(
        ...,
        description="Name of nearest distribution center",
        examples=["РЦ Сочи"],
    )
