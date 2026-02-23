"""Driver API: profile, vehicles, documents, delivery tasks, application."""
from fastapi import APIRouter

from . import (driver_application, driver_delivery_tasks, driver_documents,
               driver_profile, driver_vehicles)

router = APIRouter(prefix="/driver", tags=["Driver"])

router.include_router(driver_profile.router)
router.include_router(driver_vehicles.router)
router.include_router(driver_documents.router)
router.include_router(driver_delivery_tasks.router)
router.include_router(driver_application.router)
