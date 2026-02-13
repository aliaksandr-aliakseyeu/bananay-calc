"""API v1 router."""
from fastapi import APIRouter

from app.api.v1.endpoints import (admin_daily_checkin, admin_drivers,
                                  admin_producers, auth, calculator, countries,
                                  daily_checkin, delivery_lists,
                                  delivery_orders, delivery_point_suggestions,
                                  delivery_points, delivery_templates,
                                  distribution_centers, driver, driver_auth,
                                  producer, producer_sku, product_category,
                                  regions, sectors, settlements, tags,
                                  temperature_mode, tutorials)

api_router = APIRouter(prefix="/v1")

api_router.include_router(auth.router)
api_router.include_router(driver_auth.router)
api_router.include_router(driver.router)
api_router.include_router(daily_checkin.router)
api_router.include_router(producer.router)
api_router.include_router(producer_sku.router)
api_router.include_router(tutorials.router)
api_router.include_router(admin_producers.router)
api_router.include_router(admin_drivers.router)
api_router.include_router(admin_daily_checkin.router)
api_router.include_router(countries.router)
api_router.include_router(regions.router)
api_router.include_router(settlements.router)
api_router.include_router(sectors.router)
api_router.include_router(delivery_points.router)
api_router.include_router(delivery_point_suggestions.router)
api_router.include_router(delivery_lists.router)
api_router.include_router(delivery_templates.router)
api_router.include_router(delivery_orders.router)
api_router.include_router(distribution_centers.router)
api_router.include_router(product_category.router)
api_router.include_router(temperature_mode.router)
api_router.include_router(tags.router)
api_router.include_router(calculator.router)
