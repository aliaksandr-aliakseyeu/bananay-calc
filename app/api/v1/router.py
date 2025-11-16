"""API v1 router."""
from fastapi import APIRouter

from app.api.v1.endpoints import (countries, delivery_points, regions, sectors,
                                  tags)

api_router = APIRouter(prefix="/v1")

# Include all endpoint routers
api_router.include_router(countries.router)
api_router.include_router(regions.router)
api_router.include_router(sectors.router)
api_router.include_router(delivery_points.router)
api_router.include_router(tags.router)
