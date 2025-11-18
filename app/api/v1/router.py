"""API v1 router."""
from fastapi import APIRouter

from app.api.v1.endpoints import (calculator, countries, delivery_points,
                                  regions, sectors, tags)

api_router = APIRouter(prefix="/v1")

api_router.include_router(countries.router)
api_router.include_router(regions.router)
api_router.include_router(sectors.router)
api_router.include_router(delivery_points.router)
api_router.include_router(tags.router)
api_router.include_router(calculator.router)
