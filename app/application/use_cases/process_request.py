import asyncio
from datetime import datetime

from application.dtos import StartProcessResultDTO
from domain.entities.request import NotificationRequest, NotificationStatus
from domain.exceptions.provider import (
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderServerError,
    ProviderUnauthorizedError,
)
from domain.ports.notification_provider import NotificationProvider, ProviderResult
from domain.ports.requests_repository import RequestsRepository


class ProcessRequestUseCase:
    """
    Use case for processing a notification request.

    The request process is splitted in two steps:
        1. Start: Starts a request processing, setting its status to PROCESSING.
                Fast checks if the request is already being processed or has been sent.
        2. Deliver: Delivers the request to the external provider. This process is
                executed in background and has retry logic for network errors.
    """

    def __init__(
        self,
        requests_repository: RequestsRepository,
        notification_provider: NotificationProvider,
    ) -> None:
        self._requests_repository = requests_repository
        self._notification_provider = notification_provider

    async def start(self, request_id: str) -> StartProcessResultDTO:
        """
        Start processing a notification request.

        Args:
            request_id: The ID of the request to start processing.

        Returns:
            StartProcessResultDTO: The result of the start operation.
        """
        request = await self._requests_repository.get_by_id(request_id)
        if request is None:
            return StartProcessResultDTO(
                found=False,
                should_process=False,
                status=None,
            )

        if (
            request.status == NotificationStatus.SENT
            or request.status == NotificationStatus.PROCESSING
        ):
            return StartProcessResultDTO(
                found=True,
                should_process=False,
                status=request.status,
            )

        request.status = NotificationStatus.PROCESSING
        request.updated_at = datetime.now()
        request.error = None
        await self._requests_repository.update(request)
        return StartProcessResultDTO(
            found=True,
            should_process=True,
            status=request.status,
        )

    async def deliver(self, request_id: str) -> None:
        """
        Deliver a notification request to the external provider.

        Args:
            request_id: The ID of the request to deliver.

        Returns:
            None
        """
        request = await self._requests_repository.get_by_id(request_id)
        if request is None:  # theres no request
            return
        if (
            request.status != NotificationStatus.PROCESSING
        ):  # if its processing by another worker, skip it
            return

        try:
            provider_result = await self._send_with_retries(request)
        except (
            ProviderUnauthorizedError,
            ProviderResponseError,
            ProviderNetworkError,
            ProviderRateLimitError,
            ProviderServerError,
        ) as error:
            request.status = NotificationStatus.FAILED
            request.error = str(error)
            request.updated_at = datetime.now()
            await self._requests_repository.update(request)
            return
        except Exception as error:
            request.status = NotificationStatus.FAILED
            request.error = f"Unexpected processing error: {error}"
            request.updated_at = datetime.now()
            await self._requests_repository.update(request)
            return

        request.status = NotificationStatus.SENT
        request.provider_id = provider_result.provider_id
        request.error = None
        request.updated_at = datetime.now()
        await self._requests_repository.update(request)

    async def _send_with_retries(
        self,
        request: NotificationRequest,
    ) -> ProviderResult:
        """
        Send a notification request to the external provider with retries.

        Args:
            request: The request to send.

        Returns:
            The result of the send operation.
        """
        retry_delays_seconds = (0.2, 0.5, 1.0)
        attempts = len(retry_delays_seconds) + 1

        for attempt in range(attempts):
            try:
                return await self._notification_provider.send(
                    to=request.to,
                    message=request.message,
                    type=request.type,
                )
            except (
                ProviderRateLimitError,
                ProviderServerError,
                ProviderNetworkError,
            ):  # retryable errors
                if attempt >= len(retry_delays_seconds):
                    raise
                await asyncio.sleep(retry_delays_seconds[attempt])
            except (
                ProviderUnauthorizedError,
                ProviderResponseError,
            ):  # non-retryable errors
                raise

        raise RuntimeError("Retry loop exited without returning a provider result")
