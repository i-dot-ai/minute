from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import orjson


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as f:
        for rec in records:
            f.write(orjson.dumps(rec))
            f.write(b"\n")
