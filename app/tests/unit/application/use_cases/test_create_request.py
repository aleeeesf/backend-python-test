"""Unit tests for CreateRequestUseCase."""

import pytest

from application.dtos import CreateRequestDTO
from application.use_cases.create_request import CreateRequestUseCase
from domain.entities.request import NotificationStatus


class TestCreateRequestUseCase:
    """Test suite for CreateRequestUseCase."""

    @pytest.mark.asyncio
    async def test_creates_request_when_valid_input(self, requests_repository):
        """Create use case persists a queued request and returns its ID."""
        # Arrange
        use_case = CreateRequestUseCase(requests_repository=requests_repository)
        create_request_dto = CreateRequestDTO(
            to="user@example.com",
            message="Test notification",
            type="email",
        )

        # Act
        request_id = await use_case.execute(create_request_dto)
        stored_request = await requests_repository.get_by_id(request_id)

        # Assert
        assert request_id
        assert stored_request is not None
        assert stored_request.id == request_id
        assert stored_request.to == create_request_dto.to
        assert stored_request.message == create_request_dto.message
        assert stored_request.type == create_request_dto.type
        assert stored_request.status == NotificationStatus.QUEUED
