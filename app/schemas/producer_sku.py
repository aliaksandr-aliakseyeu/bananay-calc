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
    barcode: str | None = Field(
        None, max_length=100, description="Product barcode", examples=["4607034172015"]
    )
    sales_channel: str | None = Field(
        None, max_length=50, description="Sales channel: retail/horeca", examples=["retail"]
    )
    box_length_cm: Decimal | None = Field(
        None, ge=0.01, description="Transport box length in cm (max 2 decimal places)", examples=[40.0]
    )
    box_width_cm: Decimal | None = Field(
        None, ge=0.01, description="Transport box width in cm (max 2 decimal places)", examples=[30.0]
    )
    box_height_cm: Decimal | None = Field(
        None, ge=0.01, description="Transport box height in cm (max 2 decimal places)", examples=[25.0]
    )
    box_weight_g: Decimal | None = Field(
        None, ge=0.01, description="Transport box weight in grams (max 2 decimal places)", examples=[20000.0]
    )
    items_per_pallet: int | None = Field(
        None, ge=1, description="Number of items on euro pallet", examples=[480]
    )
    items_per_pallet_row: int | None = Field(
        None, ge=1, description="Number of items in one pallet row", examples=[24]
    )
    max_pallet_rows: int | None = Field(
        None, ge=1, description="Maximum number of rows on pallet", examples=[20]
    )
    pallet_height_cm: Decimal | None = Field(
        None, ge=0.01, description="Pallet height including pallet base in cm (max 2 decimal places)", examples=[165.0]
    )
    full_pallet_weight_kg: Decimal | None = Field(
        None, ge=0.01, description="Full pallet weight in kg (max 2 decimal places)", examples=[500.0]
    )

    @field_validator(
        'length_cm', 'width_cm', 'height_cm', 'box_length_cm', 'box_width_cm', 'box_height_cm', 'box_weight_g',
        'pallet_height_cm', 'full_pallet_weight_kg'
    )
    @classmethod
    def validate_dimensions(cls, v: Decimal | None) -> Decimal | None:
        """Validate dimensions: max 2 decimal places."""
        return validate_decimal_places(v, 2)

    @field_validator('weight_kg')
    @classmethod
    def validate_weight(cls, v: Decimal) -> Decimal:
        """Validate weight: max 3 decimal places."""
        return validate_decimal_places(v, 3)

    @field_validator('items_per_box', 'items_per_pallet', 'items_per_pallet_row', 'max_pallet_rows')
    @classmethod
    def validate_positive_integers(cls, v: int | None) -> int | None:
        """Validate integer fields: must be positive if provided."""
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
                "barcode": "4607034172015",
                "sales_channel": "retail",
                "box_length_cm": 40.0,
                "box_width_cm": 30.0,
                "box_height_cm": 25.0,
                "box_weight_g": 20000.0,
                "items_per_pallet": 480,
                "items_per_pallet_row": 24,
                "max_pallet_rows": 20,
                "pallet_height_cm": 165.0,
                "full_pallet_weight_kg": 500.0,
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
    barcode: str | None = Field(None, max_length=100, description="Product barcode")
    sales_channel: str | None = Field(None, max_length=50, description="Sales channel: retail/horeca")
    box_length_cm: Decimal | None = Field(
        None, ge=0.01, description="Transport box length in cm (max 2 decimal places)"
    )
    box_width_cm: Decimal | None = Field(
        None, ge=0.01, description="Transport box width in cm (max 2 decimal places)"
    )
    box_height_cm: Decimal | None = Field(
        None, ge=0.01, description="Transport box height in cm (max 2 decimal places)"
    )
    box_weight_g: Decimal | None = Field(
        None, ge=0.01, description="Transport box weight in grams (max 2 decimal places)"
    )
    items_per_pallet: int | None = Field(None, ge=1, description="Number of items on euro pallet")
    items_per_pallet_row: int | None = Field(None, ge=1, description="Number of items in one pallet row")
    max_pallet_rows: int | None = Field(None, ge=1, description="Maximum number of rows on pallet")
    pallet_height_cm: Decimal | None = Field(
        None, ge=0.01, description="Pallet height including pallet base in cm (max 2 decimal places)"
    )
    full_pallet_weight_kg: Decimal | None = Field(
        None, ge=0.01, description="Full pallet weight in kg (max 2 decimal places)"
    )

    @field_validator(
        'length_cm', 'width_cm', 'height_cm', 'box_length_cm', 'box_width_cm', 'box_height_cm',
        'box_weight_g', 'pallet_height_cm', 'full_pallet_weight_kg'
    )
    @classmethod
    def validate_dimensions(cls, v: Decimal | None) -> Decimal | None:
        """Validate dimensions: max 2 decimal places."""
        return validate_decimal_places(v, 2)

    @field_validator('weight_kg')
    @classmethod
    def validate_weight(cls, v: Decimal | None) -> Decimal | None:
        """Validate weight: max 3 decimal places."""
        return validate_decimal_places(v, 3)

    @field_validator('items_per_box', 'items_per_pallet', 'items_per_pallet_row', 'max_pallet_rows')
    @classmethod
    def validate_positive_integers(cls, v: int | None) -> int | None:
        """Validate integer fields: must be positive if provided."""
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
    barcode: str | None = Field(None, description="Product barcode")
    sales_channel: str | None = Field(None, description="Sales channel: retail/horeca")
    box_length_cm: Decimal | None = Field(None, description="Transport box length in cm")
    box_width_cm: Decimal | None = Field(None, description="Transport box width in cm")
    box_height_cm: Decimal | None = Field(None, description="Transport box height in cm")
    box_weight_g: Decimal | None = Field(None, description="Transport box weight in grams")
    items_per_pallet: int | None = Field(None, description="Number of items on euro pallet")
    items_per_pallet_row: int | None = Field(None, description="Number of items in one pallet row")
    max_pallet_rows: int | None = Field(None, description="Maximum number of rows on pallet")
    pallet_height_cm: Decimal | None = Field(None, description="Pallet height including pallet base in cm")
    full_pallet_weight_kg: Decimal | None = Field(None, description="Full pallet weight in kg")
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
                "barcode": "4607034172015",
                "sales_channel": "retail",
                "box_length_cm": 40.0,
                "box_width_cm": 30.0,
                "box_height_cm": 25.0,
                "box_weight_g": 20000.0,
                "items_per_pallet": 480,
                "items_per_pallet_row": 24,
                "max_pallet_rows": 20,
                "pallet_height_cm": 165.0,
                "full_pallet_weight_kg": 500.0,
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
