from application.dtos import StatusResponseDTO
from domain.ports.requests_repository import RequestsRepository


class GetRequestStatusUseCase:
    """
    Use case for getting the status of a request.
    """

    def __init__(self, requests_repository: RequestsRepository) -> None:
        self._requests_repository = requests_repository

    async def execute(self, request_id: str) -> StatusResponseDTO | None:
        """
        Execute the use case.
        Args:
            request_id: The ID of the request to get the status for.
        Returns:
            The status of the request, or None if the request is not found.
        """
        request = await self._requests_repository.get_by_id(request_id)
        if request is None:
            return None

        return StatusResponseDTO(id=request.id, status=request.status)
