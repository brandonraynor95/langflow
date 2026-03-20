import queue

import pytest
from lfx.components.docling.docling_inline import DoclingInlineComponent


class _FakeProcess:
    def __init__(self, alive: bool, exitcode: int | None):
        self._alive = alive
        self.exitcode = exitcode

    def is_alive(self):
        return self._alive


class TestDoclingInlineComponentProcessMonitoring:
    def test_wait_for_result_with_process_monitoring_reports_sigkill(self):
        component = DoclingInlineComponent()
        process = _FakeProcess(alive=False, exitcode=-9)
        result_queue = queue.Queue()

        with pytest.raises(RuntimeError, match="SIGKILL"):
            component._wait_for_result_with_process_monitoring(result_queue, process, timeout=1)

    def test_wait_for_result_with_process_monitoring_returns_result(self):
        component = DoclingInlineComponent()
        process = _FakeProcess(alive=False, exitcode=0)
        result_queue = queue.Queue()
        payload = [{"status": "ok"}]
        result_queue.put(payload)

        result = component._wait_for_result_with_process_monitoring(result_queue, process, timeout=1)

        assert result == payload
