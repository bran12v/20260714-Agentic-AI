import pytest
from structlog.testing import capture_logs

from support_api.utils import atomic_write, timed

# timed tests
def test_timed_returns_func_result():
    """The decorator must not change what the wrapped function returns."""

    @timed()
    def add(a: int, b: int) -> int:
        return a + b
    
    assert add(2,3) == 5

def test_timed_emits_log_event():
    """One @timed call -> exactly one structured log event with duration_ms."""

    @timed()
    def compute(n: int) -> int:
        return sum(range(n))
    
    with capture_logs() as logs:
        compute(100)

    assert len(logs) == 1
    assert logs[0]["event"] == "timed"
    assert logs[0]["duration_ms"] >= 0

def test_atomic_write_replaces_existing(tmp_path):
    """Happy path: contents are replaced atomically."""
    target = tmp_path / "out.txt"
    target.write_text("Original")

    with atomic_write(target) as fh:
        fh.write("NEW")

    assert target.read_text() == "NEW"