"""Region schemas."""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.country import CountryResponse


class DistributionCenterBrief(BaseModel):
    """Brief distribution center info for region response."""

    id: int
    name: str
    address: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class StandardBoxInfo(BaseModel):
    """Standard box dimensions and weight."""

    length: int = Field(..., description="Standard box length, cm", examples=[60])
    width: int = Field(..., description="Standard box width, cm", examples=[40])
    height: int = Field(..., description="Standard box height, cm", examples=[40])
    max_weight: Decimal = Field(..., description="Standard box maximum weight, kg", examples=[Decimal("30.00")])

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "length": 60,
            "width": 40,
            "height": 40,
            "max_weight": "30.00"
        }
    })


class DiscountInfo(BaseModel):
    """Discount parameters."""

    min_points: int = Field(..., description="Minimum points before discount applies", examples=[100])
    step_points: int = Field(..., description="Step increment for delivery points", examples=[50])
    initial_percent: Decimal = Field(..., description="Initial discount, %", examples=[Decimal("5.00")])
    step_percent: Decimal = Field(..., description="Discount step increment, %", examples=[Decimal("5.00")])

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "min_points": 100,
            "step_points": 50,
            "initial_percent": "5.00",
            "step_percent": "5.00"
        }
    })


class RegionPricingResponse(BaseModel):
    """Region pricing information."""

    driver_hourly_rate: Decimal = Field(
        ..., description="Driver hourly rate, RUB", examples=[Decimal("500.00")]
    )
    planned_work_hours: Decimal = Field(
        ..., description="Planned working hours", examples=[Decimal("8.00")]
    )
    fuel_price_per_liter: Decimal = Field(
        ..., description="Fuel price, RUB/L", examples=[Decimal("55.00")]
    )
    fuel_consumption_per_100km: Decimal = Field(
        ..., description="Fuel consumption, L/100km", examples=[Decimal("12.00")]
    )
    depreciation_coefficient: Decimal = Field(
        ..., description="Vehicle depreciation coefficient", examples=[Decimal("0.15")]
    )
    warehouse_processing_per_kg: Decimal = Field(
        ..., description="Warehouse processing cost per kg, RUB", examples=[Decimal("5.00")]
    )
    service_fee_per_kg: Decimal = Field(
        ..., description="Service fee per kg (company revenue), RUB",
        examples=[Decimal("10.00")]
    )
    delivery_point_cost: Decimal = Field(
        ..., description="Cost per delivery point, RUB", examples=[Decimal("150.00")]
    )
    standard_trip_weight: Decimal = Field(
        ..., description="Standard trip cargo weight, kg", examples=[Decimal("5000.00")]
    )
    standard_box: StandardBoxInfo
    discount: DiscountInfo

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "driver_hourly_rate": "500.00",
            "planned_work_hours": "8.00",
            "fuel_price_per_liter": "55.00",
            "fuel_consumption_per_100km": "12.00",
            "depreciation_coefficient": "0.15",
            "warehouse_processing_per_kg": "5.00",
            "service_fee_per_kg": "10.00",
            "delivery_point_cost": "150.00",
            "standard_trip_weight": "5000.00",
            "standard_box": {
                "length": 60,
                "width": 40,
                "height": 40,
                "max_weight": "30.00"
            },
            "discount": {
                "min_points": 100,
                "step_points": 50,
                "initial_percent": "5.00",
                "step_percent": "5.00"
            }
        }
    })

    @classmethod
    def from_pricing_model(cls, pricing):
        """Create schema from RegionPricing model."""
        return cls(
            driver_hourly_rate=pricing.driver_hourly_rate,
            planned_work_hours=pricing.planned_work_hours,
            fuel_price_per_liter=pricing.fuel_price_per_liter,
            fuel_consumption_per_100km=pricing.fuel_consumption_per_100km,
            depreciation_coefficient=pricing.depreciation_coefficient,
            warehouse_processing_per_kg=pricing.warehouse_processing_per_kg,
            service_fee_per_kg=pricing.service_fee_per_kg,
            delivery_point_cost=pricing.delivery_point_cost,
            standard_trip_weight=pricing.standard_trip_weight,
            standard_box=StandardBoxInfo(
                length=pricing.standard_box_length,
                width=pricing.standard_box_width,
                height=pricing.standard_box_height,
                max_weight=pricing.standard_box_max_weight,
            ),
            discount=DiscountInfo(
                min_points=pricing.min_points_for_discount,
                step_points=pricing.discount_step_points,
                initial_percent=pricing.initial_discount_percent,
                step_percent=pricing.discount_step_percent,
            ),
        )


class StandardBoxInfoUpdate(BaseModel):
    """Update schema for standard box."""

    length: int | None = Field(None, gt=0, description="Standard box length, cm")
    width: int | None = Field(None, gt=0, description="Standard box width, cm")
    height: int | None = Field(None, gt=0, description="Standard box height, cm")
    max_weight: Decimal | None = Field(None, gt=0, description="Standard box maximum weight, kg")


class DiscountInfoUpdate(BaseModel):
    """Update schema for discount parameters."""

    min_points: int | None = Field(None, gt=0, description="Minimum points before discount applies")
    step_points: int | None = Field(None, gt=0, description="Step increment for delivery points")
    initial_percent: Decimal | None = Field(None, ge=0, le=100, description="Initial discount, %")
    step_percent: Decimal | None = Field(None, ge=0, le=100, description="Discount step increment, %")


class RegionPricingUpdate(BaseModel):
    """Update schema for region pricing (all fields optional)."""

    driver_hourly_rate: Decimal | None = Field(None, gt=0, description="Driver hourly rate, RUB")
    planned_work_hours: Decimal | None = Field(None, gt=0, description="Planned working hours")
    fuel_price_per_liter: Decimal | None = Field(None, gt=0, description="Fuel price, RUB/L")
    fuel_consumption_per_100km: Decimal | None = Field(None, gt=0, description="Fuel consumption, L/100km")
    depreciation_coefficient: Decimal | None = Field(None, gt=0, description="Vehicle depreciation coefficient")
    warehouse_processing_per_kg: Decimal | None = Field(None, ge=0, description="Warehouse processing cost per kg, RUB")
    service_fee_per_kg: Decimal | None = Field(None, ge=0, description="Service fee per kg (company revenue), RUB")
    delivery_point_cost: Decimal | None = Field(None, gt=0, description="Cost per delivery point, RUB")
    standard_trip_weight: Decimal | None = Field(None, gt=0, description="Standard trip cargo weight, kg")
    standard_box: StandardBoxInfoUpdate | None = None
    discount: DiscountInfoUpdate | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "driver_hourly_rate": "1500.00",
                "fuel_price_per_liter": "75.00",
                "standard_box": {
                    "length": 60,
                    "max_weight": "20.00"
                },
                "discount": {
                    "min_points": 250,
                    "initial_percent": "7.00"
                }
            }
        }
    )


class RegionStatsResponse(BaseModel):
    """Region statistics."""

    distribution_centers_count: int = Field(..., description="Number of distribution centers")
    sectors_count: int = Field(..., description="Number of delivery sectors")
    settlements_count: int = Field(..., description="Number of settlements")


class RegionListResponse(BaseModel):
    """Region list item response (Variant B)."""

    id: int
    name: str
    type: str | None = Field(None, description="Region type (krai, oblast, etc.)")
    country: CountryResponse

    model_config = ConfigDict(from_attributes=True)


class RegionDetailResponse(BaseModel):
    """Region detail response with full information (Variant C)."""

    id: int
    name: str
    type: str | None = Field(None, description="Region type (krai, oblast, etc.)")
    country: CountryResponse
    distribution_centers: list[DistributionCenterBrief] = Field(
        default_factory=list,
        description="Region distribution centers"
    )
    pricing: RegionPricingResponse | None = Field(
        None,
        description="Pricing and calculation parameters (null if not configured)"
    )
    stats: RegionStatsResponse

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "name": "Краснодарский край",
            "type": "край",
            "country": {
                "id": 1,
                "name": "Россия",
                "code": "RU"
            },
            "distribution_centers": [
                {
                    "id": 1,
                    "name": "РЦ Адлер",
                    "address": "село Казачий Брод, Краснофлотская улица, 27",
                    "is_active": True
                },
                {
                    "id": 2,
                    "name": "РЦ Сочи",
                    "address": "Сочи, улица Энергетиков, 1Б",
                    "is_active": True
                }
            ],
            "pricing": {
                "driver_hourly_rate": "500.00",
                "planned_work_hours": "8.00",
                "fuel_price_per_liter": "55.00",
                "fuel_consumption_per_100km": "12.00",
                "depreciation_coefficient": "0.15",
                "warehouse_processing_per_kg": "5.00",
                "service_fee_per_kg": "10.00",
                "delivery_point_cost": "150.00",
                "standard_trip_weight": "5000.00",
                "standard_box": {
                    "length": 60,
                    "width": 40,
                    "height": 40,
                    "max_weight": "30.00"
                },
                "discount": {
                    "min_points": 100,
                    "step_points": 50,
                    "initial_percent": "5.00",
                    "step_percent": "5.00"
                }
            },
            "stats": {
                "distribution_centers_count": 8,
                "sectors_count": 45,
                "settlements_count": 123
            }
        }
    })
