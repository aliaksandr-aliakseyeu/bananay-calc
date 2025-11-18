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

    length: int = Field(..., description="Длина эталонной коробки, см", examples=[60])
    width: int = Field(..., description="Ширина эталонной коробки, см", examples=[40])
    height: int = Field(..., description="Высота эталонной коробки, см", examples=[40])
    max_weight: Decimal = Field(..., description="Максимальный вес эталонной коробки, кг", examples=[Decimal("30.00")])

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

    min_points: int = Field(..., description="Минимальное количество точек до применения скидки", examples=[100])
    step_points: int = Field(..., description="Шаг прироста количества точек доставки", examples=[50])
    initial_percent: Decimal = Field(..., description="Стартовая скидка, %", examples=[Decimal("5.00")])
    step_percent: Decimal = Field(..., description="Шаг прироста скидки, %", examples=[Decimal("5.00")])

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

    # Водитель
    driver_hourly_rate: Decimal = Field(
        ..., description="Стоимость 1 часа работы водителя, руб.", examples=[Decimal("500.00")]
    )
    planned_work_hours: Decimal = Field(
        ..., description="Часов на выполнение работы по плану", examples=[Decimal("8.00")]
    )

    # Транспорт
    fuel_price_per_liter: Decimal = Field(
        ..., description="Стоимость бензина, руб/л", examples=[Decimal("55.00")]
    )
    fuel_consumption_per_100km: Decimal = Field(
        ..., description="Расход бензина, л/100км", examples=[Decimal("12.00")]
    )
    depreciation_coefficient: Decimal = Field(
        ..., description="Коэффициент амортизации авто", examples=[Decimal("0.15")]
    )

    # РЦ
    warehouse_processing_per_kg: Decimal = Field(
        ..., description="Стоимость обработки 1 кг на РЦ, руб.", examples=[Decimal("5.00")]
    )
    service_fee_per_kg: Decimal = Field(
        ..., description="Сервисный сбор 1 кг (выручка компании), руб.",
        examples=[Decimal("10.00")]
    )

    # Адресная доставка
    delivery_point_cost: Decimal = Field(
        ..., description="Стоимость одной точки доставки, руб.", examples=[Decimal("150.00")]
    )

    # Параметры рейса
    standard_trip_weight: Decimal = Field(
        ..., description="Стандартный вес груза в рейсе, кг", examples=[Decimal("5000.00")]
    )

    # Эталонная коробка
    standard_box: StandardBoxInfo

    # Скидки
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

    length: int | None = Field(None, gt=0, description="Длина эталонной коробки, см")
    width: int | None = Field(None, gt=0, description="Ширина эталонной коробки, см")
    height: int | None = Field(None, gt=0, description="Высота эталонной коробки, см")
    max_weight: Decimal | None = Field(None, gt=0, description="Максимальный вес эталонной коробки, кг")


class DiscountInfoUpdate(BaseModel):
    """Update schema for discount parameters."""

    min_points: int | None = Field(None, gt=0, description="Минимальное количество точек до применения скидки")
    step_points: int | None = Field(None, gt=0, description="Шаг прироста количества точек доставки")
    initial_percent: Decimal | None = Field(None, ge=0, le=100, description="Стартовая скидка, %")
    step_percent: Decimal | None = Field(None, ge=0, le=100, description="Шаг прироста скидки, %")


class RegionPricingUpdate(BaseModel):
    """Update schema for region pricing (all fields optional)."""

    # Водитель
    driver_hourly_rate: Decimal | None = Field(None, gt=0, description="Стоимость 1 часа работы водителя, руб.")
    planned_work_hours: Decimal | None = Field(None, gt=0, description="Часов на выполнение работы по плану")

    # Транспорт
    fuel_price_per_liter: Decimal | None = Field(None, gt=0, description="Стоимость бензина, руб/л")
    fuel_consumption_per_100km: Decimal | None = Field(None, gt=0, description="Расход бензина, л/100км")
    depreciation_coefficient: Decimal | None = Field(None, gt=0, description="Коэффициент амортизации авто")

    # РЦ
    warehouse_processing_per_kg: Decimal | None = Field(None, ge=0, description="Стоимость обработки 1 кг на РЦ, руб.")
    service_fee_per_kg: Decimal | None = Field(None, ge=0, description="Сервисный сбор 1 кг (выручка компании), руб.")

    # Адресная доставка
    delivery_point_cost: Decimal | None = Field(None, gt=0, description="Стоимость одной точки доставки, руб.")

    # Параметры рейса
    standard_trip_weight: Decimal | None = Field(None, gt=0, description="Стандартный вес груза в рейсе, кг")

    # Эталонная коробка
    standard_box: StandardBoxInfoUpdate | None = None

    # Скидки
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

    distribution_centers_count: int = Field(..., description="Количество распределительных центров")
    sectors_count: int = Field(..., description="Количество секторов доставки")
    settlements_count: int = Field(..., description="Количество населенных пунктов")


class RegionListResponse(BaseModel):
    """Region list item response (Variant B)."""

    id: int
    name: str
    type: str | None = Field(None, description="Тип региона (край, область, и т.д.)")
    country: CountryResponse

    model_config = ConfigDict(from_attributes=True)


class RegionDetailResponse(BaseModel):
    """Region detail response with full information (Variant C)."""

    id: int
    name: str
    type: str | None = Field(None, description="Тип региона (край, область, и т.д.)")
    country: CountryResponse
    distribution_centers: list[DistributionCenterBrief] = Field(
        default_factory=list,
        description="Распределительные центры региона"
    )
    pricing: RegionPricingResponse | None = Field(
        None,
        description="Тарифы и параметры расчета (null если не настроены)"
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
