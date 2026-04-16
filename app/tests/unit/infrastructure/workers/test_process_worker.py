"""Unit tests for ProcessWorker."""

import asyncio

import pytest

from infrastructure.workers.process_worker import ProcessWorker


class FakeProcessRequestUseCase:
    """Fake process use case used by worker tests."""

    def __init__(self) -> None:
        self.delivered_request_ids: list[str] = []

    async def deliver(self, request_id: str) -> None:
        """Record delivered request IDs."""
        self.delivered_request_ids.append(request_id)


class TestProcessWorker:
    """Test suite for ProcessWorker."""

    @pytest.mark.asyncio
    async def test_dispatch_creates_and_cleans_up_task(self):
        """Worker dispatches a background task and removes it when done."""
        # Arrange
        fake_use_case = FakeProcessRequestUseCase()
        worker = ProcessWorker(process_request_use_case=fake_use_case)

        # Act
        worker.dispatch("request-123")
        assert len(worker._tasks) == 1
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        # Assert
        assert fake_use_case.delivered_request_ids == ["request-123"]
        assert len(worker._tasks) == 0
