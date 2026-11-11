"""Publish complete JSON state without truncating the previous file."""
import json
import os
import tempfile
from pathlib import Path


def write_json(path: Path, value) -> None:
    # A sibling file keeps replacement on the same filesystem. mkstemp creates
    # it with private permissions before any camera credentials are written.
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
