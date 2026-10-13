"""Tests for the path-containment guard in the local mock storage upload handler
(minute_4996 vuln-0004): a traversal path must be rejected before any filesystem write.
"""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException

from common.services.storage_services.local import mock_storage_service


class _FakeRequest:
    def __init__(self, body: bytes):
        self._body = body

    async def body(self) -> bytes:
        return self._body


@pytest.fixture(autouse=True)
def isolated_storage_root(monkeypatch, tmp_path):
    monkeypatch.setattr(mock_storage_service.settings, "LOCAL_STORAGE_PATH", str(tmp_path), raising=False)
    return tmp_path


@pytest.mark.asyncio
async def test_in_root_path_is_written(isolated_storage_root):
    root = isolated_storage_root
    await mock_storage_service.upload_file_to_mock_storage("nested/audio.mp3", _FakeRequest(b"hello"))

    written = root / "nested" / "audio.mp3"
    assert written.read_bytes() == b"hello"


@pytest.mark.asyncio
async def test_traversal_path_is_rejected_without_writing(isolated_storage_root):
    root = isolated_storage_root
    with tempfile.TemporaryDirectory() as outside:
        escape_target = Path(outside) / "escaped.txt"
        # a path that lands in the real outside dir if the guard were absent
        traversal = os.path.relpath(escape_target, root)

        with pytest.raises(HTTPException) as exc:
            await mock_storage_service.upload_file_to_mock_storage(traversal, _FakeRequest(b"pwned"))

    assert exc.value.status_code == 400
    assert not escape_target.exists()
    # nothing escaped the configured root
    assert not (root.parent / "escaped.txt").exists()
