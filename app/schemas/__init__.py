"""Pydantic schemas."""
from app.schemas.country import CountryResponse
from app.schemas.delivery_point import (BoundingBox, DeliveryPointResponse,
                                        DeliveryPointSearchRequest,
                                        DeliveryPointSearchResponse,
                                        GeoJSONPoint)
from app.schemas.distribution_center import (DistributionCenterCreate,
                                             DistributionCenterResponse,
                                             DistributionCenterUpdate)
from app.schemas.region import (DiscountInfo, DistributionCenterBrief,
                                RegionDetailResponse, RegionListResponse,
                                RegionPricingResponse, RegionPricingUpdate,
                                RegionStatsResponse, StandardBoxInfo)
from app.schemas.sector import GeoJSONPolygon, SectorResponse
from app.schemas.tag import TagResponse

__all__ = [
    "CountryResponse",
    "RegionListResponse",
    "RegionDetailResponse",
    "RegionPricingResponse",
    "RegionPricingUpdate",
    "RegionStatsResponse",
    "DistributionCenterBrief",
    "DistributionCenterCreate",
    "DistributionCenterResponse",
    "DistributionCenterUpdate",
    "StandardBoxInfo",
    "DiscountInfo",
    "SectorResponse",
    "GeoJSONPolygon",
    "DeliveryPointResponse",
    "DeliveryPointSearchRequest",
    "DeliveryPointSearchResponse",
    "BoundingBox",
    "GeoJSONPoint",
    "TagResponse",
]
