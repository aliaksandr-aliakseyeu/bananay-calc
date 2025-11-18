"""Calculator schemas."""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Request Schemas
# ============================================================================


class SupplierLocation(BaseModel):
    """Supplier location coordinates."""

    latitude: float = Field(..., ge=-90, le=90, description="Широта", examples=[43.585472])
    longitude: float = Field(..., ge=-180, le=180, description="Долгота", examples=[39.723098])


class ProductParams(BaseModel):
    """Product parameters."""

    length_cm: int = Field(..., gt=0, description="Длина товара, см", examples=[20])
    width_cm: int = Field(..., gt=0, description="Ширина товара, см", examples=[10])
    height_cm: int = Field(..., gt=0, description="Высота товара, см", examples=[10])
    weight_kg: Decimal = Field(..., gt=0, description="Вес одного товара, кг", examples=[1.0])
    items_per_box: int = Field(
        ..., gt=0, description="Количество единиц товара в коробке поставщика", examples=[15]
    )


class DeliveryParams(BaseModel):
    """Delivery parameters for estimate calculation."""

    num_points: int = Field(..., gt=0, description="Количество точек доставки", examples=[300])
    num_sectors: int | None = Field(
        None, gt=0, description="Количество секторов (опционально)", examples=[10]
    )


class CalculatorByPointsRequest(BaseModel):
    """Request for calculator by delivery points."""

    region_id: int = Field(..., description="ID региона", examples=[1])
    supplier_location: SupplierLocation = Field(..., description="Координаты поставщика")
    product: ProductParams = Field(..., description="Параметры товара")
    delivery_point_ids: list[int] = Field(
        ..., min_length=1, description="Список ID точек доставки"
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
                "delivery_point_ids": [
                    4510, 328, 1299, 4877, 2590, 3941, 210, 1784, 3420, 67,
                    4992, 812, 145, 3055, 2378, 4688, 129, 980, 4112, 2225,
                    356, 4920, 1877, 4311, 299, 1678, 3840, 4711, 248,
                    1950, 1221, 4899, 3310, 444, 2887, 1520, 4630, 174, 2600,
                    990, 3999, 4700, 502, 1408, 330, 2789, 470, 140,
                    3811, 4555, 2120, 4870, 389, 1750, 4300, 2011, 250,
                    3920, 4666, 1280, 4990, 910, 2870, 350, 1600, 222,
                    4012, 3800, 1744, 4788, 520, 2566, 1420, 310, 1833,
                    2750, 4955, 780, 4900, 998, 3666, 4440, 2077, 490,
                    3333, 2910, 4050, 1270, 4701, 1888, 275, 3101, 1450, 4998
                ]
            }
        }
    )


class CalculatorEstimateRequest(BaseModel):
    """Request for calculator estimate."""

    region_id: int = Field(..., description="ID региона", examples=[1])
    supplier_location: SupplierLocation = Field(..., description="Координаты поставщика")
    product: ProductParams = Field(..., description="Параметры товара")
    delivery: DeliveryParams = Field(..., description="Параметры доставки")

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


# ============================================================================
# Response Schemas
# ============================================================================


class CalculatorByPointsResponse(BaseModel):
    """Response for calculator by delivery points."""

    items_in_standard_box: int = Field(
        ...,
        description="Количество товара поставщика в одной эталонной коробке "
        "с учетом ограничения по весу",
        examples=[18],
    )
    cost_per_item: Decimal = Field(
        ...,
        description="Стоимость доставки одной единицы товара поставщика, руб.",
        examples=[38.29],
    )
    cost_per_supplier_box: Decimal = Field(
        ...,
        description="Стоимость доставки одной коробки товара поставщика, руб.",
        examples=[574.35],
    )
    delivery_points_used: int = Field(
        ..., description="Количество использованных точек доставки", examples=[150]
    )
    delivery_points_ignored: int = Field(
        ..., description="Количество проигнорированных точек доставки", examples=[5]
    )
    sectors_count: int = Field(
        ...,
        description="Количество уникальных секторов, в которые попали точки доставки",
        examples=[3],
    )
    distance_to_dc_km: Decimal = Field(
        ...,
        description="Расстояние до ближайшего распределительного центра, км",
        examples=[15.50],
    )
    nearest_dc_name: str = Field(
        ...,
        description="Название ближайшего распределительного центра",
        examples=["РЦ Сочи"],
    )


class CalculatorEstimateResponse(BaseModel):
    """Response for calculator estimate."""

    items_in_standard_box: int = Field(
        ...,
        description="Количество товара поставщика в одной эталонной коробке "
        "с учетом ограничения по весу",
        examples=[18],
    )
    cost_per_item: Decimal = Field(
        ...,
        description="Стоимость доставки одной единицы товара поставщика, руб.",
        examples=[38.29],
    )
    cost_per_supplier_box: Decimal = Field(
        ...,
        description="Стоимость доставки одной коробки товара поставщика, руб.",
        examples=[574.35],
    )
    distance_to_dc_km: Decimal = Field(
        ...,
        description="Расстояние до ближайшего распределительного центра, км",
        examples=[15.50],
    )
    nearest_dc_name: str = Field(
        ...,
        description="Название ближайшего распределительного центра",
        examples=["РЦ Сочи"],
    )
