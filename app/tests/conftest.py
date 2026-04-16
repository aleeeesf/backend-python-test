"""Shared fixtures for unit and integration tests."""

import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure tests resolve imports from the app runtime root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application.use_cases.create_request import CreateRequestUseCase
from application.use_cases.get_request_status import GetRequestStatusUseCase
from application.use_cases.process_request import ProcessRequestUseCase
from core.dependencies import (
    get_create_request_use_case,
    get_notification_provider,
    get_process_dispatcher,
    get_process_request_use_case,
    get_request_status_use_case,
)
from domain.entities.request import NotificationRequest, NotificationStatus
from domain.exceptions.provider import (
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderServerError,
    ProviderUnauthorizedError,
)
from domain.ports.notification_provider import ProviderResult
from domain.ports.process_dispatcher import ProcessDispatcher
from infrastructure.repositories.in_memory_requests_repository import (
    InMemoryRequestsRepository,
)
from main import app as fastapi_app


class FakeNotificationProvider:
    """Simple fake provider configurable per test."""

    def __init__(self) -> None:
        self.result = ProviderResult(provider_id="p-1234", status="delivered")
        self.side_effects: list[Exception] = []
        self.calls: list[dict[str, str]] = []

    async def send(self, to: str, message: str, type: str) -> ProviderResult:
        """Record the call and return the configured response."""
        self.calls.append(
            {
                "to": to,
                "message": message,
                "type": type,
            }
        )
        if self.side_effects:
            raise self.side_effects.pop(0)
        return self.result


class StubProcessDispatcher(ProcessDispatcher):
    """Test dispatcher that records enqueued requests without background execution."""

    def __init__(self) -> None:
        self.dispatched_request_ids: list[str] = []

    def dispatch(self, request_id: str) -> None:
        """Record dispatched request IDs."""
        self.dispatched_request_ids.append(request_id)


# ==============================================================================
# Repository Fixtures
# ==============================================================================


@pytest.fixture(name="requests_repository")
def _requests_repository_fixture() -> InMemoryRequestsRepository:
    """In-memory repository used by tests."""
    return InMemoryRequestsRepository()


# ==============================================================================
# Provider Fixtures
# ==============================================================================


@pytest.fixture(name="fake_notification_provider")
def _fake_notification_provider_fixture() -> FakeNotificationProvider:
    """Fake external notification provider."""
    return FakeNotificationProvider()


@pytest.fixture(name="stub_process_dispatcher")
def _stub_process_dispatcher_fixture() -> StubProcessDispatcher:
    """Dispatcher stub for route integration tests."""
    return StubProcessDispatcher()


# ==============================================================================
# Data Fixtures
# ==============================================================================


@pytest.fixture(name="queued_request")
def _queued_request_fixture() -> NotificationRequest:
    """Queued request ready to be processed."""
    return NotificationRequest(
        id="request-queued",
        to="user@example.com",
        message="Test notification",
        type="email",
        status=NotificationStatus.QUEUED,
    )


@pytest.fixture(name="processing_request")
def _processing_request_fixture() -> NotificationRequest:
    """Request already in processing state."""
    return NotificationRequest(
        id="request-processing",
        to="user@example.com",
        message="Test notification",
        type="email",
        status=NotificationStatus.PROCESSING,
    )


@pytest.fixture(name="sent_request")
def _sent_request_fixture() -> NotificationRequest:
    """Request already delivered successfully."""
    return NotificationRequest(
        id="request-sent",
        to="user@example.com",
        message="Test notification",
        type="email",
        status=NotificationStatus.SENT,
        provider_id="p-9999",
    )


@pytest.fixture(name="failed_request")
def _failed_request_fixture() -> NotificationRequest:
    """Request that failed previously."""
    return NotificationRequest(
        id="request-failed",
        to="user@example.com",
        message="Test notification",
        type="email",
        status=NotificationStatus.FAILED,
        error="Previous failure",
    )


@pytest.fixture(name="provider_errors")
def _provider_errors_fixture() -> dict[str, Exception]:
    """Provider exception catalog used by tests."""
    return {
        "unauthorized": ProviderUnauthorizedError("Invalid API key"),
        "rate_limit": ProviderRateLimitError("Rate limit exceeded"),
        "server": ProviderServerError("External server error"),
        "network": ProviderNetworkError("Provider timeout"),
        "response": ProviderResponseError("Invalid provider response payload"),
    }


# ==============================================================================
# Integration Fixtures
# ==============================================================================


@pytest.fixture(name="client")
def _client_fixture(
    requests_repository: InMemoryRequestsRepository,
    fake_notification_provider: FakeNotificationProvider,
    stub_process_dispatcher: StubProcessDispatcher,
) -> Generator[TestClient, None, None]:
    """FastAPI test client with dependency overrides."""

    def _get_create_request_use_case() -> CreateRequestUseCase:
        return CreateRequestUseCase(requests_repository)

    def _get_process_request_use_case() -> ProcessRequestUseCase:
        return ProcessRequestUseCase(
            requests_repository=requests_repository,
            notification_provider=fake_notification_provider,
        )

    def _get_request_status_use_case() -> GetRequestStatusUseCase:
        return GetRequestStatusUseCase(requests_repository)

    fastapi_app.dependency_overrides[get_create_request_use_case] = (
        _get_create_request_use_case
    )
    fastapi_app.dependency_overrides[get_process_request_use_case] = (
        _get_process_request_use_case
    )
    fastapi_app.dependency_overrides[get_request_status_use_case] = (
        _get_request_status_use_case
    )
    fastapi_app.dependency_overrides[get_notification_provider] = lambda: (
        fake_notification_provider
    )
    fastapi_app.dependency_overrides[get_process_dispatcher] = lambda: (
        stub_process_dispatcher
    )

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()
