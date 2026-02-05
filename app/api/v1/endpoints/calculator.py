"""Calculator API endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.schemas.calculator import (CalculatorByPointsRequest,
                                    CalculatorByPointsResponse,
                                    CalculatorEstimateRequest,
                                    CalculatorEstimateResponse)
from app.services.calculator_service import CalculatorService

router = APIRouter(prefix="/calculator", tags=["calculator"])

logger = logging.getLogger(__name__)


@router.post(
    "/by-points",
    response_model=CalculatorByPointsResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate delivery cost by delivery points",
    description=(
        "Calculate delivery cost based on specific delivery points with quantities. "
        "The total quantity is calculated as the sum of all point quantities, "
        "and the number of regions is determined from unique regions containing the points."
    ),
)
async def calculate_by_points(
    request: CalculatorByPointsRequest,
    db: AsyncSession = Depends(get_db),
) -> CalculatorByPointsResponse:
    """
    Calculate delivery costs using specific delivery points with quantities.

    - **region_id**: Region ID
    - **supplier_location**: Supplier coordinates (latitude, longitude)
    - **product**: Product parameters (dimensions, weight, quantity per box)
    - **point_quantities**: List of delivery points with their quantities

    Returns delivery cost for the supplier's product and information about
    the total quantity and number of unique regions.
    """
    try:
        calculator = CalculatorService(db)

        point_quantities = [
            (pq.point_id, pq.quantity) for pq in request.point_quantities
        ]

        result = await calculator.calculate_by_points(
            region_id=request.region_id,
            supplier_lat=request.supplier_location.latitude,
            supplier_lon=request.supplier_location.longitude,
            product=request.product,
            point_quantities=point_quantities,
        )

        return CalculatorByPointsResponse(**result)

    except ValueError as e:
        logger.warning("Validation error in calculate_by_points: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Unexpected error in calculate_by_points: %s",
            str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during calculation"
        )


@router.post(
    "/estimate",
    response_model=CalculatorEstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate delivery cost estimate",
    description=(
        "Calculate estimated delivery cost based on the number of points. "
        "If the number of sectors is not specified, the maximum for the region is used."
    ),
)
async def calculate_estimate(
    request: CalculatorEstimateRequest,
    db: AsyncSession = Depends(get_db),
) -> CalculatorEstimateResponse:
    """
    Calculate delivery costs using estimated numbers.

    - **region_id**: Region ID
    - **supplier_location**: Supplier coordinates (latitude, longitude)
    - **product**: Product parameters (dimensions, weight, quantity per box)
    - **delivery**: Delivery parameters (number of points, optionally number of sectors)

    Returns delivery cost for the supplier's product.
    """
    try:
        calculator = CalculatorService(db)

        result = await calculator.calculate_estimate(
            region_id=request.region_id,
            supplier_lat=request.supplier_location.latitude,
            supplier_lon=request.supplier_location.longitude,
            product=request.product,
            num_points=request.delivery.num_points,
            num_sectors=request.delivery.num_sectors,
        )

        return CalculatorEstimateResponse(**result)

    except ValueError as e:
        logger.warning("Validation error in calculate_estimate: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Unexpected error in calculate_estimate: %s",
            str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during calculation"
        )
