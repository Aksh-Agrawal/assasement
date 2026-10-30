"""OS locks serialize cycles and elect one scheduler across Qt and systemd."""
import os
import time
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def file_lock(path, *, blocking=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    stream.seek(0)
    if path.stat().st_size == 0:
        stream.write(b"0")
        stream.flush()
    acquired = False
    try:
        while not acquired:
            try:
                if os.name == "nt":
                    import msvcrt
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except (OSError, BlockingIOError):
                if not blocking:
                    break
                time.sleep(0.1)
        yield acquired
    finally:
        if acquired:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()
