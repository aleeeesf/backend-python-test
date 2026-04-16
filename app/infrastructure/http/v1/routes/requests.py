from fastapi import APIRouter, Depends, HTTPException, Response, status

from application.dtos import CreateRequestDTO, CreateResponseDTO, StatusResponseDTO
from application.use_cases.create_request import CreateRequestUseCase
from application.use_cases.get_request_status import GetRequestStatusUseCase
from application.use_cases.process_request import ProcessRequestUseCase
from core.dependencies import (
    get_create_request_use_case,
    get_process_dispatcher,
    get_process_request_use_case,
    get_request_status_use_case,
)
from domain.entities.request import NotificationStatus
from domain.ports.process_dispatcher import ProcessDispatcher

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("", status_code=201, response_model=CreateResponseDTO)
async def create_request(
    request: CreateRequestDTO,
    create_request_use_case: CreateRequestUseCase = Depends(
        get_create_request_use_case
    ),
) -> CreateResponseDTO:
    """
    Create a new request.

    Args:
        request: CreateRequestDTO - The request to create.
        create_request_use_case: CreateRequestUseCase - The use case to create the request.

    Returns:
        CreateResponseDTO: The created request.
    """
    request_id = await create_request_use_case.execute(request)
    return CreateResponseDTO(id=request_id)


@router.post("/{request_id}/process")
async def process_request(
    request_id: str,
    process_request_use_case: ProcessRequestUseCase = Depends(
        get_process_request_use_case
    ),
    process_dispatcher: ProcessDispatcher = Depends(get_process_dispatcher),
) -> Response:
    """
    Process a request.

    Args:
        request_id: The ID of the request to process.
        process_request_use_case: ProcessRequestUseCase - The use case to process the request.
        process_dispatcher: ProcessDispatcher - The dispatcher to process the request.

    Returns:
        Response: FastAPI Response with status code 200 or 202.
    """
    process_result = await process_request_use_case.start(request_id)
    if not process_result.found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
        )

    if process_result.status == NotificationStatus.SENT:
        return Response(status_code=status.HTTP_200_OK)

    if process_result.should_process:
        process_dispatcher.dispatch(request_id=request_id)  # process in background
        return Response(status_code=status.HTTP_202_ACCEPTED)

    if process_result.status == NotificationStatus.PROCESSING:
        return Response(status_code=status.HTTP_202_ACCEPTED)

    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.get("/{request_id}", response_model=StatusResponseDTO)
async def get_request_status(
    request_id: str,
    request_status_use_case: GetRequestStatusUseCase = Depends(
        get_request_status_use_case
    ),
) -> StatusResponseDTO:
    """
    Get the status of a request.

    Args:
        request_id: The ID of the request to get the status of.
        request_status_use_case: GetRequestStatusUseCase - The use case to get the status of the request.

    Returns:
        StatusResponseDTO: The status of the request.
    """
    status_response = await request_status_use_case.execute(request_id)
    if status_response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )
    return status_response
