from pathlib import Path

import pytest

from common.audio.ffmpeg import convert_to_mp3, get_duration, get_num_audio_channels
from tests.marks import requires_audio_data
from tests.utils import FileTypeTests

pytestmark = [requires_audio_data]


def get_normal_data():
    return list(Path(".data").joinpath("test_audio").joinpath(FileTypeTests.NORMAL).iterdir())


@pytest.fixture
def filename(request):
    return request.param


@pytest.mark.parametrize("filename", get_normal_data(), indirect=True)
def test_get_duration(filename: Path):
    result = get_duration(filename)
    assert result > 0


@pytest.mark.parametrize("filename", get_normal_data(), indirect=True)
def test_get_num_audio_channels(filename: Path):
    result = get_num_audio_channels(filename)
    assert result > -1


@pytest.mark.parametrize("filename", get_normal_data(), indirect=True)
def test_convert_to_mp3(filename: Path):
    result = Path(convert_to_mp3(filename))
    assert result.suffix == ".mp3"
    assert result.exists()
    assert result.stat().st_size > 0
    result.unlink()
    assert not result.exists()
