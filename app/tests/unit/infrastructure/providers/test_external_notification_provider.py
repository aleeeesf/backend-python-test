"""Unit tests for ExternalNotificationProvider."""

import httpx
import pytest

from domain.exceptions.provider import (
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderServerError,
    ProviderUnauthorizedError,
)
from infrastructure.providers.external_notification_provider import (
    ExternalNotificationProvider,
)


class FakeResponse:
    """Simple fake HTTP response."""

    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, object]:
        """Return response payload."""
        return self._payload


class FakeAsyncClient:
    """Simple fake async client for provider tests."""

    def __init__(
        self,
        response: FakeResponse | None = None,
        error: Exception | None = None,
        timeout: float | None = None,
    ) -> None:
        self._response = response
        self._error = error
        self.timeout = timeout
        self.requests: list[dict[str, object]] = []

    async def __aenter__(self) -> "FakeAsyncClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Exit async context manager."""
        return None

    async def post(
        self,
        url: str,
        json: dict[str, str],
        headers: dict[str, str],
    ) -> FakeResponse:
        """Record request and return configured response."""
        self.requests.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
            }
        )
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


class TestExternalNotificationProvider:
    """Test suite for ExternalNotificationProvider."""

    @pytest.mark.asyncio
    async def test_returns_provider_result_when_provider_succeeds(self, monkeypatch):
        """Provider adapter returns parsed provider result on HTTP 200."""
        # Arrange
        fake_client = FakeAsyncClient(
            response=FakeResponse(
                status_code=200,
                payload={"provider_id": "p-1234", "status": "delivered"},
            )
        )
        monkeypatch.setattr(
            "infrastructure.providers.external_notification_provider.httpx.AsyncClient",
            lambda timeout: fake_client,
        )
        provider = ExternalNotificationProvider(
            api_url="http://provider:3001",
            api_key="test-dev-2026",
        )

        # Act
        result = await provider.send(
            to="user@example.com",
            message="Test notification",
            type="email",
        )

        # Assert
        assert result.provider_id == "p-1234"
        assert result.status == "delivered"
        assert fake_client.requests == [
            {
                "url": "http://provider:3001/v1/notify",
                "json": {
                    "to": "user@example.com",
                    "message": "Test notification",
                    "type": "email",
                },
                "headers": {
                    "X-API-Key": "test-dev-2026",
                    "Content-Type": "application/json",
                },
            }
        ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("status_code", "payload", "expected_exception"),
        [
            (401, {"detail": "Invalid API key"}, ProviderUnauthorizedError),
            (429, {"detail": "Rate limit exceeded"}, ProviderRateLimitError),
            (500, {"detail": "External server error"}, ProviderServerError),
            (418, {"detail": "Unexpected"}, ProviderResponseError),
        ],
    )
    async def test_raises_expected_error_for_http_status(
        self,
        monkeypatch,
        status_code,
        payload,
        expected_exception,
    ):
        """Provider adapter maps non-200 responses to domain exceptions."""
        # Arrange
        fake_client = FakeAsyncClient(
            response=FakeResponse(status_code=status_code, payload=payload)
        )
        monkeypatch.setattr(
            "infrastructure.providers.external_notification_provider.httpx.AsyncClient",
            lambda timeout: fake_client,
        )
        provider = ExternalNotificationProvider(
            api_url="http://provider:3001",
            api_key="test-dev-2026",
        )

        # Act / Assert
        with pytest.raises(expected_exception):
            await provider.send(
                to="user@example.com",
                message="Test notification",
                type="email",
            )

    @pytest.mark.asyncio
    async def test_raises_response_error_when_payload_is_invalid(self, monkeypatch):
        """Provider adapter rejects malformed success payloads."""
        # Arrange
        fake_client = FakeAsyncClient(
            response=FakeResponse(status_code=200, payload={"status": "delivered"})
        )
        monkeypatch.setattr(
            "infrastructure.providers.external_notification_provider.httpx.AsyncClient",
            lambda timeout: fake_client,
        )
        provider = ExternalNotificationProvider(
            api_url="http://provider:3001",
            api_key="test-dev-2026",
        )

        # Act / Assert
        with pytest.raises(ProviderResponseError):
            await provider.send(
                to="user@example.com",
                message="Test notification",
                type="email",
            )

    @pytest.mark.asyncio
    async def test_raises_network_error_when_provider_times_out(self, monkeypatch):
        """Provider adapter maps timeout exceptions to ProviderNetworkError."""
        # Arrange
        fake_client = FakeAsyncClient(error=httpx.TimeoutException("timeout"))
        monkeypatch.setattr(
            "infrastructure.providers.external_notification_provider.httpx.AsyncClient",
            lambda timeout: fake_client,
        )
        provider = ExternalNotificationProvider(
            api_url="http://provider:3001",
            api_key="test-dev-2026",
        )

        # Act / Assert
        with pytest.raises(ProviderNetworkError):
            await provider.send(
                to="user@example.com",
                message="Test notification",
                type="email",
            )
