from evals.audio_generation.src.utils.parsing_utils import save_audio


def test_save_audio(tmp_path, monkeypatch):
    """Test that save_audio correctly saves audio bytes and returns correct path."""
    audio_bytes = b"test audio data"
    output_file = "output.mp3"

    monkeypatch.setattr("evals.audio_generation.src.utils.parsing_utils.AUDIO_GEN_DIR", tmp_path)

    saved_path = save_audio(audio_bytes, output_file, target_dir="output")

    full_path = tmp_path / saved_path

    assert full_path.exists()
    assert full_path.suffix == ".mp3"
    assert full_path.stem.startswith("output_")
    assert full_path.read_bytes() == audio_bytes
