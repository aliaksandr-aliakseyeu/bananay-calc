"""Delivery point schemas."""
from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    """Bounding box для фильтрации по координатам."""

    min_lng: float = Field(..., description="Минимальная долгота (западная граница)")
    min_lat: float = Field(..., description="Минимальная широта (южная граница)")
    max_lng: float = Field(..., description="Максимальная долгота (восточная граница)")
    max_lat: float = Field(..., description="Максимальная широта (северная граница)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "min_lng": 39.7,
            "min_lat": 43.5,
            "max_lng": 39.8,
            "max_lat": 43.6
        }
    })


class DeliveryPointSearchRequest(BaseModel):
    """Request schema для поиска точек доставки."""

    region_id: int = Field(..., description="ID региона", examples=[1])
    only_in_sectors: bool = Field(
        False,
        description="true = только точки в секторах, false = все точки региона"
    )
    bbox: BoundingBox | None = Field(
        None,
        description="Фильтр по прямоугольнику координат (опционально)"
    )
    tag_ids: list[int] | None = Field(
        None,
        description="Фильтр по тэгам (опционально, OR логика)"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "region_id": 1,
            "only_in_sectors": True,
            "bbox": {
                "min_lng": 39.7,
                "min_lat": 43.5,
                "max_lng": 39.8,
                "max_lat": 43.6
            },
            "tag_ids": [1, 2, 3]
        }
    })


class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry."""

    type: str = Field(default="Point", description="Geometry type")
    coordinates: list[float] = Field(
        ...,
        description="Point coordinates [longitude, latitude]"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "type": "Point",
            "coordinates": [39.723098, 43.585472]
        }
    })


class DeliveryPointResponse(BaseModel):
    """Delivery point response schema."""

    id: int
    name: str
    type: str | None = Field(None, description="Тип точки доставки")
    title: str | None = Field(None, description="Заголовок / дополнительное описание")
    address: str | None = Field(None, description="Адрес")
    address_comment: str | None = Field(None, description="Комментарий к адресу")
    landmark: str | None = Field(None, description="Ориентир")
    location: GeoJSONPoint = Field(..., description="Координаты в формате GeoJSON")
    phone: str | None = Field(None, description="Телефон(ы)")
    mobile: str | None = Field(None, description="Мобильный(е)")
    email: str | None = Field(None, description="Email(ы)")
    schedule: str | None = Field(None, description="Расписание работы")
    is_active: bool = Field(..., description="Активна ли точка доставки")

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "name": "Магазин Пятёрочка",
            "type": "Магазин",
            "title": "Пятёрочка на Краснофлотской",
            "address": "село Казачий Брод, Краснофлотская улица, 27",
            "address_comment": "Вход со стороны парковки",
            "landmark": "Рядом с автобусной остановкой",
            "location": {
                "type": "Point",
                "coordinates": [39.723098, 43.585472]
            },
            "phone": "+7 (862) 123-45-67",
            "mobile": "+7 (999) 123-45-67",
            "email": "shop@example.com",
            "schedule": "Пн-Вс: 08:00-22:00",
            "is_active": True
        }
    })


class DeliveryPointSearchResponse(BaseModel):
    """Search response with total count and items."""

    total: int = Field(..., description="Общее количество найденных точек доставки")
    items: list[DeliveryPointResponse] = Field(..., description="Список точек доставки")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total": 150,
            "items": [
                {
                    "id": 1,
                    "name": "Магазин Пятёрочка",
                    "type": "Магазин",
                    "title": "Пятёрочка на Краснофлотской",
                    "address": "село Казачий Брод, Краснофлотская улица, 27",
                    "address_comment": "Вход со стороны парковки",
                    "landmark": "Рядом с автобусной остановкой",
                    "location": {
                        "type": "Point",
                        "coordinates": [39.723098, 43.585472]
                    },
                    "phone": "+7 (862) 123-45-67",
                    "mobile": "+7 (999) 123-45-67",
                    "email": "shop@example.com",
                    "schedule": "Пн-Вс: 08:00-22:00",
                    "is_active": True
                }
            ]
        }
    })
