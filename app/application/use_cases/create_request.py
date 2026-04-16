from uuid import uuid4

from application.dtos import CreateRequestDTO
from domain.entities.request import NotificationRequest, NotificationStatus
from domain.ports.requests_repository import RequestsRepository


class CreateRequestUseCase:
    """
    Use case for creating a new request.
    """

    def __init__(self, requests_repository: RequestsRepository) -> None:
        """
        Initialize the use case.

        Args:
            requests_repository: RequestsRepository - The repository for requests.
        """
        self._requests_repository = requests_repository

    async def execute(self, create_dto: CreateRequestDTO) -> str:
        """
        Execute the use case.

        Args:
            create_dto: CreateRequestDTO - The request to create.

        Returns:
            str: The ID of the created request.
        """
        request_id = str(uuid4())
        new_request = NotificationRequest(
            id=request_id,
            to=create_dto.to,
            message=create_dto.message,
            type=create_dto.type,
            status=NotificationStatus.QUEUED,
        )
        await self._requests_repository.save(new_request)
        return request_id
