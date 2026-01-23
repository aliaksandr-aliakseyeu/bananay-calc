"""Producer SKU schemas."""
from datetime import datetime
from decimal import ROUND_DOWN, Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.product_category import ProductCategoryResponse
from app.schemas.temperature_mode import TemperatureModeResponse


def validate_decimal_places(value: Decimal | None, max_places: int) -> Decimal | None:
    """Validate and round decimal to max places."""
    if value is None:
        return None
    # Round down to max_places
    quantize_str = '0.' + '0' * max_places
    return value.quantize(Decimal(quantize_str), rounding=ROUND_DOWN)


class ProducerSKUBase(BaseModel):
    """Base schema for Producer SKU."""

    name: str = Field(
        ..., min_length=1, max_length=200, description="SKU name", examples=["Бананы премиум 1кг"]
    )
    sku_code: str | None = Field(
        None, max_length=100, description="SKU code/articul", examples=["BAN-001"]
    )
    description: str | None = Field(None, description="SKU description")
    length_cm: Decimal = Field(
        ..., ge=0.01, description="Product length in cm (max 2 decimal places)", examples=[20.5]
    )
    width_cm: Decimal = Field(
        ..., ge=0.01, description="Product width in cm (max 2 decimal places)", examples=[15.3]
    )
    height_cm: Decimal = Field(
        ..., ge=0.01, description="Product height in cm (max 2 decimal places)", examples=[10.8]
    )
    weight_kg: Decimal = Field(
        ..., ge=0.001, description="Weight of one item in kg (max 3 decimal places)", examples=[1.0]
    )
    items_per_box: int | None = Field(
        None, description="Number of items in producer's box (optional)", examples=[20]
    )

    @field_validator('length_cm', 'width_cm', 'height_cm')
    @classmethod
    def validate_dimensions(cls, v: Decimal) -> Decimal:
        """Validate dimensions: max 2 decimal places."""
        return validate_decimal_places(v, 2)

    @field_validator('weight_kg')
    @classmethod
    def validate_weight(cls, v: Decimal) -> Decimal:
        """Validate weight: max 3 decimal places."""
        return validate_decimal_places(v, 3)

    @field_validator('items_per_box')
    @classmethod
    def validate_items_per_box(cls, v: int | None) -> int | None:
        """Validate items per box: must be positive if provided."""
        if v is not None and v <= 0:
            raise ValueError('must be greater than 0')
        return v
    product_category_id: int | None = Field(None, description="Product category ID", examples=[1])
    temperature_mode_id: int | None = Field(None, description="Temperature mode ID", examples=[2])
    is_active: bool = Field(True, description="Is SKU active")


class ProducerSKUCreate(ProducerSKUBase):
    """Schema for creating a Producer SKU."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Бананы премиум 1кг",
                "sku_code": "BAN-001",
                "description": "Отборные бананы в упаковке 1кг",
                "length_cm": 20.5,
                "width_cm": 15.3,
                "height_cm": 10.8,
                "weight_kg": 1.0,
                "items_per_box": 20,
                "product_category_id": 1,
                "temperature_mode_id": 2,
                "is_active": True,
            }
        }
    )


class ProducerSKUUpdate(BaseModel):
    """Schema for updating a Producer SKU. All fields are optional."""

    name: str | None = Field(None, min_length=1, max_length=200, description="SKU name")
    sku_code: str | None = Field(None, max_length=100, description="SKU code/articul")
    description: str | None = Field(None, description="SKU description")
    length_cm: Decimal | None = Field(
        None, ge=0.01, description="Product length in cm (max 2 decimal places)"
    )
    width_cm: Decimal | None = Field(
        None, ge=0.01, description="Product width in cm (max 2 decimal places)"
    )
    height_cm: Decimal | None = Field(
        None, ge=0.01, description="Product height in cm (max 2 decimal places)"
    )
    weight_kg: Decimal | None = Field(
        None, ge=0.001, description="Weight of one item in kg (max 3 decimal places)"
    )
    items_per_box: int | None = Field(None, description="Number of items in producer's box (optional)")

    @field_validator('length_cm', 'width_cm', 'height_cm')
    @classmethod
    def validate_dimensions(cls, v: Decimal | None) -> Decimal | None:
        """Validate dimensions: max 2 decimal places."""
        return validate_decimal_places(v, 2)

    @field_validator('weight_kg')
    @classmethod
    def validate_weight(cls, v: Decimal | None) -> Decimal | None:
        """Validate weight: max 3 decimal places."""
        return validate_decimal_places(v, 3)

    @field_validator('items_per_box')
    @classmethod
    def validate_items_per_box(cls, v: int | None) -> int | None:
        """Validate items per box: must be positive if provided."""
        if v is not None and v <= 0:
            raise ValueError('must be greater than 0')
        return v

    product_category_id: int | None = Field(None, description="Product category ID")
    temperature_mode_id: int | None = Field(None, description="Temperature mode ID")
    is_active: bool | None = Field(None, description="Is SKU active")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Обновлённое название",
                "description": "Новое описание",
                "is_active": False,
            }
        }
    )


class ProducerSKUResponse(BaseModel):
    """Schema for Producer SKU response (list view)."""

    id: int = Field(..., description="SKU ID")
    name: str = Field(..., description="SKU name")
    sku_code: str | None = Field(None, description="SKU code/articul")
    is_active: bool = Field(..., description="Is SKU active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Бананы премиум 1кг",
                "sku_code": "BAN-001",
                "is_active": True,
                "created_at": "2026-01-20T12:00:00Z",
                "updated_at": "2026-01-20T12:00:00Z",
            }
        },
    )


class ProducerSKUDetailResponse(BaseModel):
    """Schema for Producer SKU detail response."""

    id: int = Field(..., description="SKU ID")
    name: str = Field(..., description="SKU name")
    sku_code: str | None = Field(None, description="SKU code/articul")
    description: str | None = Field(None, description="SKU description")
    length_cm: Decimal = Field(..., description="Product length in cm")
    width_cm: Decimal = Field(..., description="Product width in cm")
    height_cm: Decimal = Field(..., description="Product height in cm")
    weight_kg: Decimal = Field(..., description="Weight of one item in kg")
    items_per_box: int | None = Field(None, description="Number of items in producer's box (optional)")
    product_category: ProductCategoryResponse | None = Field(None, description="Product category")
    temperature_mode: TemperatureModeResponse | None = Field(None, description="Temperature mode")
    is_active: bool = Field(..., description="Is SKU active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Бананы премиум 1кг",
                "sku_code": "BAN-001",
                "description": "Отборные бананы в упаковке 1кг",
                "length_cm": 20.5,
                "width_cm": 15.3,
                "height_cm": 10.8,
                "weight_kg": 1.0,
                "items_per_box": 20,
                "product_category": {
                    "id": 1,
                    "name": "Фрукты",
                    "slug": "fruits",
                    "is_active": True,
                },
                "temperature_mode": {
                    "id": 2,
                    "name": "Охлаждённые",
                    "slug": "cold",
                    "is_active": True,
                },
                "is_active": True,
                "created_at": "2026-01-20T12:00:00Z",
                "updated_at": "2026-01-20T12:00:00Z",
            }
        },
    )

