import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from audio_worker import ffmpeg


def test_conversion_timeout_is_configured():
    with (
        patch.object(Path, "is_file", return_value=True),
        patch("audio_worker.ffmpeg.subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 1)) as run,
        pytest.raises(RuntimeError),
    ):
        ffmpeg.convert_to_mp3(Path("audio.wav"), Path("audio.mp3"), timeout=600)

    assert run.call_args.kwargs["timeout"] == 600


@pytest.mark.parametrize("probe", [ffmpeg.get_num_channels, ffmpeg.get_duration])
def test_probe_timeout_is_configured(probe):
    with patch.object(Path, "is_file", return_value=True), patch("audio_worker.ffmpeg.subprocess.run") as run:
        run.side_effect = subprocess.TimeoutExpired("ffprobe", 1)
        with pytest.raises(RuntimeError):
            probe(Path("audio.wav"), timeout=60)

    assert run.call_args.kwargs["timeout"] == 60
