from application.dtos import StatusResponseDTO
from domain.ports.requests_repository import RequestsRepository


class GetRequestStatusUseCase:
    def __init__(self, requests_repository: RequestsRepository) -> None:
        self._requests_repository = requests_repository

    async def execute(self, request_id: str) -> StatusResponseDTO | None:
        request = await self._requests_repository.get_by_id(request_id)
        if request is None:
            return None

        return StatusResponseDTO(id=request.id, status=request.status)
