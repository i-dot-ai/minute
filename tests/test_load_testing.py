import wave
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from load_testing.run import check_response, upload_a_file


def test_check_response_includes_error_body():
    response = requests.Response()
    response.status_code = 401
    response._content = b"not signed in"  # noqa: SLF001

    with pytest.raises(RuntimeError, match="Create recording failed \\(401\\): not signed in"):
        check_response(response, "Create recording")


def test_upload_streams_file_and_reports_failing_step(tmp_path: Path):
    audio = tmp_path / "audio.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\0" * 16)
    session = Mock()
    session.post.return_value = Mock(status_code=200, json=lambda: {"id": "recording", "upload_url": "upload"})
    session.put.return_value = Mock(
        status_code=403, text="expired upload", raise_for_status=Mock(side_effect=requests.HTTPError)
    )

    with (
        patch("load_testing.run.requests.Session", return_value=session),
        pytest.raises(RuntimeError, match="Upload recording failed \\(403\\): expired upload"),
    ):
        upload_a_file(audio, "cookie")

    uploaded_file = session.put.call_args.kwargs["data"]
    assert not isinstance(uploaded_file, bytes)
