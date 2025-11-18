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
        "Рассчитать стоимость доставки на основе конкретных точек доставки. "
        "Количество точек и секторов определяется автоматически из переданных ID."
    ),
)
async def calculate_by_points(
    request: CalculatorByPointsRequest,
    db: AsyncSession = Depends(get_db),
) -> CalculatorByPointsResponse:
    """
    Calculate delivery costs using specific delivery points.

    - **region_id**: ID региона
    - **supplier_location**: Координаты поставщика (широта, долгота)
    - **product**: Параметры товара (размеры, вес, количество в коробке)
    - **delivery_point_ids**: Список ID точек доставки

    Возвращает стоимость доставки для товара поставщика и информацию о
    количестве использованных/проигнорированных точек доставки.
    """
    try:
        calculator = CalculatorService(db)

        result = await calculator.calculate_by_points(
            region_id=request.region_id,
            supplier_lat=request.supplier_location.latitude,
            supplier_lon=request.supplier_location.longitude,
            product=request.product,
            delivery_point_ids=request.delivery_point_ids,
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
        "Рассчитать приблизительную стоимость доставки на основе количества точек. "
        "Если количество секторов не указано, используется максимум для региона."
    ),
)
async def calculate_estimate(
    request: CalculatorEstimateRequest,
    db: AsyncSession = Depends(get_db),
) -> CalculatorEstimateResponse:
    """
    Calculate delivery costs using estimated numbers.

    - **region_id**: ID региона
    - **supplier_location**: Координаты поставщика (широта, долгота)
    - **product**: Параметры товара (размеры, вес, количество в коробке)
    - **delivery**: Параметры доставки (количество точек, опционально количество секторов)

    Возвращает стоимость доставки для товара поставщика.
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
