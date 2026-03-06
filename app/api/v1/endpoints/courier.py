"""Courier API: profile, vehicles, documents, delivery tasks, application."""
from fastapi import APIRouter

from . import (courier_application, courier_daily_checkin, courier_delivery_tasks,
               courier_documents, courier_profile, courier_vehicles)

router = APIRouter(prefix="/courier", tags=["Courier"])

router.include_router(courier_profile.router)
router.include_router(courier_vehicles.router)
router.include_router(courier_documents.router)
router.include_router(courier_application.router)
router.include_router(courier_delivery_tasks.router)
