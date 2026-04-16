"""Unit tests for GetRequestStatusUseCase."""

import pytest

from application.use_cases.get_request_status import GetRequestStatusUseCase


class TestGetRequestStatusUseCase:
    """Test suite for GetRequestStatusUseCase."""

    @pytest.mark.asyncio
    async def test_returns_none_when_request_does_not_exist(self, requests_repository):
        """Status use case returns None for unknown request IDs."""
        # Arrange
        use_case = GetRequestStatusUseCase(requests_repository=requests_repository)

        # Act
        result = await use_case.execute("missing-request")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_status_when_request_exists(
        self,
        requests_repository,
        queued_request,
    ):
        """Status use case returns request ID and status when request exists."""
        # Arrange
        use_case = GetRequestStatusUseCase(requests_repository=requests_repository)
        await requests_repository.save(queued_request)

        # Act
        result = await use_case.execute(queued_request.id)

        # Assert
        assert result is not None
        assert result.id == queued_request.id
        assert result.status == queued_request.status
