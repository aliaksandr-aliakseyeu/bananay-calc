"""Public landing page endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.landing import TrialDeliveryLeadRequest
from app.services.email_service import email_service

router = APIRouter(prefix="/landing", tags=["Landing"])


@router.post("/trial-delivery-request", status_code=status.HTTP_202_ACCEPTED)
async def create_trial_delivery_request(payload: TrialDeliveryLeadRequest) -> dict:
    """Receive trial delivery lead from landing and send notification email."""
    try:
        email_service.send_trial_delivery_lead(
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process trial delivery request",
        ) from exc

    return {"message": "Trial delivery request accepted"}
