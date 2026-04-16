import asyncio

from application.use_cases.process_request import ProcessRequestUseCase
from domain.ports.process_dispatcher import ProcessDispatcher


class ProcessWorker(ProcessDispatcher):
    """
    Worker that processes requests in the background.
    """

    def __init__(self, process_request_use_case: ProcessRequestUseCase) -> None:
        self._process_request_use_case = process_request_use_case
        self._tasks: set[asyncio.Task[None]] = set()

    def dispatch(self, request_id: str) -> None:
        """
        Creates a background task to process the request.

        Args:
            request_id: The ID of the request to process.

        Returns:
            None
        """
        task = asyncio.create_task(self._process_request_use_case.deliver(request_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
