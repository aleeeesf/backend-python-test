"""Unit tests for ProcessRequestUseCase."""

import pytest

from application.use_cases.process_request import ProcessRequestUseCase
from domain.entities.request import NotificationStatus


class TestProcessRequestUseCaseStart:
    """Test suite for ProcessRequestUseCase.start."""

    @pytest.mark.asyncio
    async def test_returns_not_found_when_request_does_not_exist(
        self,
        requests_repository,
        fake_notification_provider,
    ):
        """Start returns not found for unknown request IDs."""
        # Arrange
        use_case = ProcessRequestUseCase(
            requests_repository=requests_repository,
            notification_provider=fake_notification_provider,
        )

        # Act
        result = await use_case.start("missing-request")

        # Assert
        assert result.found is False
        assert result.should_process is False
        assert result.status is None

    @pytest.mark.asyncio
    async def test_marks_request_as_processing_when_request_is_queued(
        self,
        requests_repository,
        fake_notification_provider,
        queued_request,
    ):
        """Start transitions queued requests to processing."""
        # Arrange
        await requests_repository.save(queued_request)
        use_case = ProcessRequestUseCase(
            requests_repository=requests_repository,
            notification_provider=fake_notification_provider,
        )

        # Act
        result = await use_case.start(queued_request.id)
        stored_request = await requests_repository.get_by_id(queued_request.id)

        # Assert
        assert result.found is True
        assert result.should_process is True
        assert result.status == NotificationStatus.PROCESSING
        assert stored_request is not None
        assert stored_request.status == NotificationStatus.PROCESSING
        assert stored_request.error is None

    @pytest.mark.asyncio
    async def test_skips_processing_when_request_is_already_sent(
        self,
        requests_repository,
        fake_notification_provider,
        sent_request,
    ):
        """Start does not reprocess sent requests."""
        # Arrange
        await requests_repository.save(sent_request)
        use_case = ProcessRequestUseCase(
            requests_repository=requests_repository,
            notification_provider=fake_notification_provider,
        )

        # Act
        result = await use_case.start(sent_request.id)

        # Assert
        assert result.found is True
        assert result.should_process is False
        assert result.status == NotificationStatus.SENT


class TestProcessRequestUseCaseDeliver:
    """Test suite for ProcessRequestUseCase.deliver."""

    @pytest.mark.asyncio
    async def test_marks_request_as_sent_when_provider_succeeds(
        self,
        requests_repository,
        fake_notification_provider,
        processing_request,
    ):
        """Deliver marks a processing request as sent on provider success."""
        # Arrange
        await requests_repository.save(processing_request)
        use_case = ProcessRequestUseCase(
            requests_repository=requests_repository,
            notification_provider=fake_notification_provider,
        )

        # Act
        await use_case.deliver(processing_request.id)
        stored_request = await requests_repository.get_by_id(processing_request.id)

        # Assert
        assert stored_request is not None
        assert stored_request.status == NotificationStatus.SENT
        assert (
            stored_request.provider_id == fake_notification_provider.result.provider_id
        )
        assert stored_request.error is None
        assert len(fake_notification_provider.calls) == 1

    @pytest.mark.asyncio
    async def test_marks_request_as_failed_when_provider_is_unauthorized(
        self,
        requests_repository,
        fake_notification_provider,
        processing_request,
        provider_errors,
    ):
        """Deliver fails immediately on unauthorized provider errors."""
        # Arrange
        fake_notification_provider.side_effects = [provider_errors["unauthorized"]]
        await requests_repository.save(processing_request)
        use_case = ProcessRequestUseCase(
            requests_repository=requests_repository,
            notification_provider=fake_notification_provider,
        )

        # Act
        await use_case.deliver(processing_request.id)
        stored_request = await requests_repository.get_by_id(processing_request.id)

        # Assert
        assert stored_request is not None
        assert stored_request.status == NotificationStatus.FAILED
        assert stored_request.error == "Invalid API key"
        assert len(fake_notification_provider.calls) == 1

    @pytest.mark.asyncio
    async def test_retries_and_marks_request_as_sent_when_transient_error_recovers(
        self,
        requests_repository,
        fake_notification_provider,
        processing_request,
        provider_errors,
    ):
        """Deliver retries transient provider errors and succeeds if provider recovers."""
        # Arrange
        fake_notification_provider.side_effects = [provider_errors["rate_limit"]]
        await requests_repository.save(processing_request)
        use_case = ProcessRequestUseCase(
            requests_repository=requests_repository,
            notification_provider=fake_notification_provider,
        )

        # Act
        await use_case.deliver(processing_request.id)
        stored_request = await requests_repository.get_by_id(processing_request.id)

        # Assert
        assert stored_request is not None
        assert stored_request.status == NotificationStatus.SENT
        assert stored_request.error is None
        assert len(fake_notification_provider.calls) == 2

    @pytest.mark.asyncio
    async def test_marks_request_as_failed_when_unexpected_error_happens(
        self,
        requests_repository,
        fake_notification_provider,
        processing_request,
    ):
        """Deliver marks request as failed on unexpected processing errors."""
        # Arrange
        fake_notification_provider.side_effects = [RuntimeError("Boom")]
        await requests_repository.save(processing_request)
        use_case = ProcessRequestUseCase(
            requests_repository=requests_repository,
            notification_provider=fake_notification_provider,
        )

        # Act
        await use_case.deliver(processing_request.id)
        stored_request = await requests_repository.get_by_id(processing_request.id)

        # Assert
        assert stored_request is not None
        assert stored_request.status == NotificationStatus.FAILED
        assert stored_request.error == "Unexpected processing error: Boom"
        assert len(fake_notification_provider.calls) == 1
