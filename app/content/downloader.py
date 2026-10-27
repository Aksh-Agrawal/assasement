"""Bounded temporary-file downloads for untrusted remote pack bytes."""

import os
import tempfile
from pathlib import Path

from app.content.catalog import RemotePack
from app.content.client import ContentApiClient


class DownloadSizeError(RuntimeError):
    pass


def download_pack_to_temp(
    client: ContentApiClient,
    pack: RemotePack,
    *,
    temp_directory: Path,
    max_bytes: int,
) -> Path:
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    if pack.size_bytes > max_bytes:
        raise DownloadSizeError(
            f"Catalog size {pack.size_bytes} exceeds configured maximum {max_bytes}"
        )
    temp_directory.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix="pack-", suffix=".download", dir=temp_directory)
    temporary = Path(filename)
    actual = 0
    try:
        with os.fdopen(descriptor, "wb") as output, client.stream_pack(pack) as response:
            for chunk in response.iter_bytes():
                actual += len(chunk)
                if actual > pack.size_bytes or actual > max_bytes:
                    raise DownloadSizeError("Download exceeded declared or configured size")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if actual != pack.size_bytes:
            raise DownloadSizeError(f"Expected {pack.size_bytes} bytes, received {actual}")
        return temporary
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
