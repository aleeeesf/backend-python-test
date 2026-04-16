from functools import lru_cache

from application.use_cases.create_request import CreateRequestUseCase
from application.use_cases.get_request_status import GetRequestStatusUseCase
from application.use_cases.process_request import ProcessRequestUseCase
from core.settings import Settings, settings
from domain.ports.notification_provider import NotificationProvider
from domain.ports.process_dispatcher import ProcessDispatcher
from infrastructure.providers.external_notification_provider import (
    ExternalNotificationProvider,
)
from infrastructure.repositories.in_memory_requests_repository import (
    InMemoryRequestsRepository,
)
from infrastructure.workers.process_worker import ProcessWorker


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get the application settings instance."""
    return settings


@lru_cache(maxsize=1)
def get_requests_repository() -> InMemoryRequestsRepository:
    """Get the requests repository instance."""
    return InMemoryRequestsRepository()


def get_create_request_use_case() -> CreateRequestUseCase:
    """Get the CreateRequestUseCase instance."""
    return CreateRequestUseCase(get_requests_repository())


def get_notification_provider() -> NotificationProvider:
    """Get the notification provider instance."""
    app_settings = get_settings()
    provider_settings = app_settings.external_provider
    return ExternalNotificationProvider(
        api_url=provider_settings.api_url,
        api_key=provider_settings.api_key,
    )


def get_process_request_use_case() -> ProcessRequestUseCase:
    """Get the ProcessRequestUseCase instance."""
    return ProcessRequestUseCase(
        requests_repository=get_requests_repository(),
        notification_provider=get_notification_provider(),
    )


def get_request_status_use_case() -> GetRequestStatusUseCase:
    """Get the GetRequestStatusUseCase instance."""
    return GetRequestStatusUseCase(get_requests_repository())


@lru_cache(maxsize=1)
def get_process_dispatcher() -> ProcessDispatcher:
    """Get the process dispatcher instance."""
    return ProcessWorker(get_process_request_use_case())
