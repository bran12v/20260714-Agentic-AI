"""Shared functionality or resources."""

from functools import wraps
import time
import structlog
from pathlib import Path
from contextlib import contextmanager
import os
_log = structlog.get_logger(__name__)

def timed(label: str | None = None): # Decorator Factory
    """Log the wall-clock duration of the decorated callable.
    
    Used as '@timed()' parentheses are requried or '@timed(label='custom-label').
    The optional label overrides the function's qualified name in the log event.
    """

    def decorator(func):
        event_label = label or func.__qualname__

        @wraps(func)
        def wrapper(*args, **kwargs):
            started = time.perf_counter() # before, preprocessing
            try:
                return func(*args, **kwargs) # this is the actual function call of the function this is decorating.
            finally:
                duration_ms = round((time.perf_counter() - started) * 1000, 2) # after, postprocessing
                _log.info("timed", label=event_label, duration_ms=duration_ms)
        
        return wrapper
    
    return decorator


"""
    contextmanager is a special decorator that you 
    can use to essentially handle all of your file
    interactions.
"""
@contextmanager # __enter__, __exit__
def atomic_write(path: Path, encoding: str = "utf-8"):
    """Write to a tempfile next to 'path', then rename on clean exit.
    
    On exception, the tempfile is removed and the original file is left untocuhed.
    Callers get a writable file handle as the 'as' value.
    """
    tmp = path.with_suffix(path.suffix + ".tmp") # ralph.txt.tmp
    try:
        with tmp.open("w", encoding=encoding) as fh:
            yield fh # generator function
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise
    else:
        os.replace(tmp, path) # final write that persists any changes made.


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tempdir:
        target = Path(tempdir) / "demo.txt"
        target.write_text("ORIGINAL")
        print(f"Original file contents: {target.read_text()}")

        # Happy Path: contents get replaced
        with atomic_write(target) as fh:
            fh.write("NEW CONTENTS")
        print(f"After happy path: {target.read_text()}")

        # Sad Path (failure)
        try:
            with atomic_write(target) as fh:
                fh.write("WOULD BE REPLACEMENT")
                raise RuntimeError("Boom")
        except RuntimeError:
            print(f"After failure:      {target.read_text()}")

        leftover = target.with_suffix(".txt.tmp")
        print(f"Tempfile left behind: {leftover.exists()}")






    # import structlog

    # structlog.configure()

    # @timed()
    # def compute(n: int) -> int:
    #     """Sum 0...n-1"""
    #     return sum(range(n))

    # @timed(label="big-compute")
    # def compute_big(n: int) -> int:
    #     """Sum 0...n-1"""
    #     return sum(range(n))
    
    # print(f"compute results:        {compute(1_000_000)}")
    # print(f"compute_big results:    {compute_big(1_000_000)}")
    # print(f"compute.__name__:       {compute.__name__}")