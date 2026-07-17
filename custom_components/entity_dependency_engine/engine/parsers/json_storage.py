from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class StorageReadError(RuntimeError):
    pass

def read_storage_json(path: str | Path) -> dict[str, Any]:
    storage_path = Path(path)
    if not storage_path.exists():
        raise StorageReadError(f"Storage file does not exist: {storage_path}")
    if not storage_path.is_file():
        raise StorageReadError(f"Storage path is not a file: {storage_path}")
    try:
        raw = storage_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StorageReadError(f"Could not read {storage_path}: {exc}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StorageReadError(
            f"Invalid JSON in {storage_path}: line {exc.lineno}, column {exc.colno}"
        ) from exc
    if not isinstance(payload, dict):
        raise StorageReadError(f"Expected JSON object in {storage_path}")
    return payload
